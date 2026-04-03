"""Internal high-coverage DNS resolver for nftables set management.

This module replaces the previous external ``berserker_resolver`` dependency
with a modern, typed implementation that keeps its high-coverage
multi-nameserver resolution strategy while adding bounded worker-pool execution
and per-run result caching.
"""

from __future__ import annotations

import _thread
from collections.abc import Iterable
from dataclasses import dataclass, field
import importlib
import logging
import os
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Address
from typing import Any, Callable


DEFAULT_FALLBACK_NAMESERVERS = [
    # Google Public DNS.
    "8.8.8.8",
    "8.8.4.4",
    # Cloudflare.
    "1.1.1.1",
    "1.0.0.1",
    # Quad9.
    "9.9.9.9",
]
DEFAULT_MAX_WORKERS_CAP = 16
DEFAULT_MAX_WORKERS_FLOOR = 4
DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_TRIES_PER_NAMESERVER = 4
DEFAULT_RECORD_TYPE = "A"
WWW_PATTERN = re.compile(r"(?:www\.){1}(.+\..+)", re.IGNORECASE)
WWW_COMBINE_PATTERN = re.compile(r"(?:www\.)?(.+\..+)", re.IGNORECASE)


def get_default_max_workers() -> int:
    """Return the adaptive default worker count for bulk DNS resolution."""

    cpu_count = os.cpu_count() or 1
    return min(
        DEFAULT_MAX_WORKERS_CAP,
        max(DEFAULT_MAX_WORKERS_FLOOR, cpu_count * 2),
    )


@dataclass(slots=True)
class ResolverConfig:
    """Configuration for :class:`DnsResolver`.

    :param nameservers: Nameservers used for high-coverage lookups.
    :type nameservers: list[str]
    :param fallback_nameservers: Public fallback nameservers.
    :type fallback_nameservers: list[str]
    :param tries_per_nameserver: Number of attempts per nameserver.
    :type tries_per_nameserver: int
    :param timeout_seconds: Per-query timeout applied to the backend resolver.
    :type timeout_seconds: float
    :param max_workers: Maximum number of worker threads for bulk resolution.
    :type max_workers: int
    :param record_type: DNS record type.
    :type record_type: str
    :param verbose: Whether :meth:`resolve` should return per-nameserver exceptions.
    :type verbose: bool
    :param www: Whether to add or strip ``www.`` variants during resolution.
    :type www: bool
    :param www_combine: Whether to combine ``www`` and non-``www`` answers.
    :type www_combine: bool
    """

    nameservers: list[str]
    fallback_nameservers: list[str] = field(
        default_factory=lambda: list(DEFAULT_FALLBACK_NAMESERVERS),
    )
    tries_per_nameserver: int = DEFAULT_TRIES_PER_NAMESERVER
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_workers: int = field(default_factory=get_default_max_workers)
    record_type: str = DEFAULT_RECORD_TYPE
    verbose: bool = False
    www: bool = False
    www_combine: bool = False


@dataclass(slots=True)
class CachedResolution:
    """Cached per-domain resolution result.

    :param records: Sorted IPv4 answers for the domain.
    :type records: tuple[str, ...]
    """

    records: tuple[str, ...]


class DomainResolutionError(RuntimeError):
    """Raised when a domain cannot be resolved by the high-coverage path."""

    def __init__(self, domain: str, errors: dict[str, Exception]) -> None:
        """Initialize the exception.

        :param domain: Domain that failed to resolve.
        :type domain: str
        :param errors: Per-nameserver lookup failures.
        :type errors: dict[str, Exception]
        """

        self.domain: str = domain
        self.errors: dict[str, Exception] = errors
        error_messages = ", ".join(
            f"{nameserver}: {error}" for nameserver, error in sorted(errors.items())
        )
        super().__init__(f"Could not resolve {domain}: {error_messages or 'no result'}")


class DnsResolver:
    """High-coverage DNS resolver with bounded worker concurrency."""

    def __init__(
        self,
        config: ResolverConfig,
        logger: logging.Logger | None = None,
        backend_factory: Callable[[], Any] | None = None,
        dns_exception_type: type[Exception] | None = None,
    ) -> None:
        """Initialize the resolver.

        :param config: Resolver configuration.
        :type config: ResolverConfig
        :param logger: Logger used for progress and error reporting.
        :type logger: logging.Logger | None
        :param backend_factory: Optional backend factory for testing.
        :type backend_factory: Callable[[], Any] | None
        :param dns_exception_type: Optional DNS exception base class for testing.
        :type dns_exception_type: type[Exception] | None
        :raises ValueError: If concurrency or retry counts are invalid.
        """

        self._validate_config(config)
        self.config: ResolverConfig = config
        self.logger: logging.Logger = logger or logging.getLogger(self.__class__.__name__)
        self.nameservers: list[str] = list(config.nameservers)
        self.fallback_nameservers: list[str] = list(config.fallback_nameservers)
        self.tries: int = config.tries_per_nameserver
        self.timeout: float = config.timeout_seconds
        self.threads: int = config.max_workers
        self.qname: str = config.record_type
        self.verbose: bool = config.verbose
        self.www: bool = config.www
        self.www_combine: bool = config.www_combine
        self._thread_local: threading.local = threading.local()
        self._cache_lock: _thread.LockType = threading.Lock()
        self._cache: dict[str, CachedResolution] = {}
        self._backend_factory: Callable[[], Any] = backend_factory or self._build_backend_factory()
        self._dns_exception_type: type[Exception] = dns_exception_type or self._load_dns_exception_type()

    def query(self, domain: str, nameserver: str | None = None) -> Any:
        """Run a single DNS query using one nameserver.

        :param domain: Domain to resolve.
        :type domain: str
        :param nameserver: Optional explicit nameserver.
        :type nameserver: str | None
        :return: Backend answer object from dnspython-compatible resolver.
        :rtype: Any
        :raises RuntimeError: If no nameservers are configured.
        :raises Exception: Any backend DNS exception raised by the query.
        """

        if not self.nameservers:
            raise RuntimeError("No nameservers configured for DNS resolution")
        selected_nameserver: str = nameserver or random.choice(self.nameservers)
        backend = self._get_backend()
        backend.nameservers = [selected_nameserver]
        return self._backend_resolve(backend, domain)

    def resolve(self, domains: Iterable[str]) -> dict[str, set[str]] | dict[str, Any]:
        """Resolve many domains using the high-coverage strategy.

        :param domains: Domains to resolve.
        :type domains: Iterable[str]
        :return: Successful results, optionally wrapped with per-nameserver errors.
        :rtype: dict[str, set[str]] | dict[str, Any]
        """

        success, error = self._resolve_domains(domains)
        if self.verbose:
            return {"success": success, "error": error}
        return success

    def resolve_text(self, domain: str) -> list[str]:
        """Resolve one domain and return sorted IPv4 text answers.

        :param domain: Domain to resolve.
        :type domain: str
        :return: Sorted IPv4 answers.
        :rtype: list[str]
        :raises DomainResolutionError: If the domain cannot be resolved.
        """

        cache_key: str = self._cache_key(domain)
        cached: CachedResolution | None = self._get_cached_resolution(cache_key)
        if cached is not None:
            return list(cached.records)
        success, error = self._resolve_domains([domain])
        self._store_cache_entries(success)
        records: set[str] = success.get(cache_key, set())
        if not records:
            raise DomainResolutionError(domain, dict(error.get(cache_key, {})))
        return sorted(records)

    def resolve_many_text(self, domains: Iterable[str]) -> dict[str, list[str]]:
        """Resolve many domains and return sorted IPv4 text answers.

        This method uses the per-run cache when available and queries DNS for
        uncached domains through :meth:`prefetch`.

        :param domains: Domains to resolve.
        :type domains: Iterable[str]
        :return: Mapping of normalized domain key to sorted IPv4 answers.
        :rtype: dict[str, list[str]]
        """

        requested_domains: list[str] = self._deduplicate_domains(domains)
        self.prefetch(requested_domains)
        results: dict[str, list[str]] = {}
        with self._cache_lock:
            for domain in requested_domains:
                cache_key: str = self._cache_key(domain)
                cached: CachedResolution | None = self._cache.get(cache_key)
                if cached is not None and cached.records:
                    results[cache_key] = list(cached.records)
        return results

    def prefetch(self, domains: Iterable[str]) -> None:
        """Warm the per-run cache for many domains.

        This stores successful lookups only. Failed lookups are left uncached so
        later direct resolution attempts can retry.

        :param domains: Domains to resolve.
        :type domains: Iterable[str]
        """

        unique_domains: list[str] = self._deduplicate_domains(domains)
        pending_domains: list[str] = self._uncached_domains(unique_domains)
        if not pending_domains:
            return
        self.logger.debug("Prefetching DNS for domains: %s", pending_domains)
        success, _errors = self._resolve_domains(pending_domains)
        self._store_cache_entries(success)

    def _build_backend_factory(self) -> Callable[[], Any]:
        """Create the default backend factory.

        :return: Factory that builds configured dnspython resolver backends.
        :rtype: Callable[[], Any]
        """

        dns_resolver_module = importlib.import_module("dns.resolver")

        def factory() -> Any:
            backend = dns_resolver_module.Resolver(configure=False)
            backend.lifetime = self.timeout
            return backend

        return factory

    def _load_dns_exception_type(self) -> type[Exception]:
        """Load the backend DNS exception type.

        :return: Base DNS exception type.
        :rtype: type[Exception]
        """

        dns_exception_module = importlib.import_module("dns.exception")
        return dns_exception_module.DNSException

    def _get_backend(self) -> Any:
        """Return a thread-local backend instance.

        :return: Thread-local backend.
        :rtype: Any
        """

        backend: Any | None = getattr(self._thread_local, "backend", None)
        if backend is None:
            backend = self._backend_factory()
            self._thread_local.backend = backend
        return backend

    def _backend_resolve(self, backend: Any, domain: str) -> Any:
        """Run a backend query against one domain.

        :param backend: dnspython-compatible resolver backend.
        :type backend: Any
        :param domain: Domain to resolve.
        :type domain: str
        :return: Backend answer object.
        :rtype: Any
        """

        if hasattr(backend, "resolve"):
            return backend.resolve(domain, self.qname)
        return backend.query(domain, self.qname)

    def _resolve_domains(
        self,
        domains: Iterable[str],
    ) -> tuple[dict[str, set[str]], dict[str, dict[str, Exception]]]:
        """Resolve many domains without touching the cache.

        :param domains: Domains to resolve.
        :type domains: Iterable[str]
        :return: Successful answers and per-nameserver errors.
        :rtype: tuple[dict[str, set[str]], dict[str, dict[str, Exception]]]
        """

        tasks: list[tuple[str, str]] = list(self._bind(domains))
        success: dict[str, set[str]] = {}
        error: dict[str, dict[str, Exception]] = {}
        if not tasks:
            return success, error
        max_workers: int = min(self.threads, len(tasks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for task, answer in executor.map(self._run_task, tasks):
                self._build_result(task, answer, success, error)
        return success, error

    def _run_task(self, task: tuple[str, str]) -> tuple[tuple[str, str], list[str] | Exception]:
        """Execute a single resolution task.

        :param task: Query domain and nameserver.
        :type task: tuple[str, str]
        :return: Task and either text answers or an exception.
        :rtype: tuple[tuple[str, str], list[str] | Exception]
        """

        query_domain: str
        nameserver: str
        query_domain, nameserver = task
        backend = self._get_backend()
        backend.nameservers = [nameserver]
        try:
            answer = self._backend_resolve(backend, query_domain)
            answer_text: list[str] = sorted({record.to_text() for record in answer})
            return task, answer_text
        except self._dns_exception_type as error:
            return task, error

    def _build_result(
        self,
        task: tuple[str, str],
        answer: list[str] | Exception,
        success: dict[str, set[str]],
        error: dict[str, dict[str, Exception]],
    ) -> None:
        """Merge one task result into the aggregate output.

        :param task: Query domain and nameserver.
        :type task: tuple[str, str]
        :param answer: Successful answers or an exception.
        :type answer: list[str] | Exception
        :param success: Successful result accumulator.
        :type success: dict[str, set[str]]
        :param error: Error accumulator.
        :type error: dict[str, dict[str, Exception]]
        """

        query_domain: str
        nameserver: str
        query_domain, nameserver = task
        domain_key: str = self._result_domain_key(query_domain)
        if isinstance(answer, Exception):
            error.setdefault(domain_key, {})[nameserver] = answer
            return
        success.setdefault(domain_key, set()).update(answer)

    def _bind(self, domains: Iterable[str]) -> Iterable[tuple[str, str]]:
        """Expand domains into repeated nameserver tasks.

        :param domains: Domains to resolve.
        :type domains: Iterable[str]
        :return: Query domain and nameserver pairs.
        :rtype: Iterable[tuple[str, str]]
        """

        for domain in self._deduplicate_domains(domains):
            for _ in range(self.tries):
                for nameserver in self.nameservers:
                    for query_domain in self._query_variants(domain):
                        yield query_domain, nameserver

    def _query_variants(self, domain: str) -> list[str]:
        """Build query variants for one domain.

        :param domain: Input domain.
        :type domain: str
        :return: Query variants.
        :rtype: list[str]
        """

        if not self.www:
            return [domain]
        match: re.Match[str] | None = WWW_PATTERN.match(domain)
        if match is None:
            return [domain, f"www.{domain}"]
        return [domain, match.group(1)]

    def _result_domain_key(self, domain: str) -> str:
        """Normalize a domain key for result aggregation.

        :param domain: Domain to normalize.
        :type domain: str
        :return: Normalized result key.
        :rtype: str
        """

        if not self.www_combine:
            return domain
        match: re.Match[str] | None = WWW_COMBINE_PATTERN.match(domain)
        if match is None:
            return domain
        return match.group(1)

    def _cache_key(self, domain: str) -> str:
        """Return the cache lookup key for a domain.

        :param domain: Input domain.
        :type domain: str
        :return: Cache key.
        :rtype: str
        """

        return self._result_domain_key(domain) if self.www_combine else domain

    def _store_cache_entries(self, success: dict[str, set[str]]) -> None:
        """Store successful resolution results in the cache.

        :param success: Successful answers grouped by domain key.
        :type success: dict[str, set[str]]
        """

        with self._cache_lock:
            for domain_key, records in sorted(success.items()):
                self._cache[domain_key] = CachedResolution(records=tuple(sorted(records)))

    def _get_cached_resolution(self, cache_key: str) -> CachedResolution | None:
        """Return a cached resolution for ``cache_key``.

        :param cache_key: Cache key to retrieve.
        :type cache_key: str
        :return: Cached resolution if available.
        :rtype: CachedResolution | None
        """

        with self._cache_lock:
            return self._cache.get(cache_key)

    def _uncached_domains(self, domains: Iterable[str]) -> list[str]:
        """Return requested domains missing from the cache.

        :param domains: Domains to inspect.
        :type domains: Iterable[str]
        :return: Domains requiring lookup.
        :rtype: list[str]
        """

        pending_domains: list[str] = []
        with self._cache_lock:
            for domain in domains:
                if self._cache_key(domain) not in self._cache:
                    pending_domains.append(domain)
        return pending_domains

    def _deduplicate_domains(self, domains: Iterable[str]) -> list[str]:
        """Deduplicate domains while preserving order.

        :param domains: Input domains.
        :type domains: Iterable[str]
        :return: Deduplicated domains.
        :rtype: list[str]
        """

        seen: set[str] = set()
        unique_domains: list[str] = []
        for domain in domains:
            normalized_domain: str = domain.strip()
            if not normalized_domain or normalized_domain in seen:
                continue
            seen.add(normalized_domain)
            unique_domains.append(normalized_domain)
        return unique_domains

    @staticmethod
    def _validate_config(config: ResolverConfig) -> None:
        """Validate configuration values.

        :param config: Resolver configuration to validate.
        :type config: ResolverConfig
        :raises ValueError: If concurrency or retry counts are invalid.
        """

        if config.tries_per_nameserver < 1:
            raise ValueError("tries_per_nameserver must be at least 1")
        if config.max_workers < 1:
            raise ValueError("max_workers must be at least 1")

    @staticmethod
    def is_ipv4_address(value: str) -> bool:
        """Return whether ``value`` is a valid IPv4 address.

        :param value: Value to validate.
        :type value: str
        :return: ``True`` for valid IPv4 input.
        :rtype: bool
        """

        try:
            IPv4Address(value)
        except ValueError:
            return False
        return True

"""Tests for the internal DNS resolver."""

from __future__ import annotations

from collections.abc import Callable
import threading
import time
from typing import Any, cast

import pytest
# pyright: reportImplicitRelativeImport=false
from dns_resolver import DnsResolver, DomainResolutionError, ResolverConfig


class FakeDnsException(Exception):
    """Fake DNS exception for resolver tests."""


class FakeRecord:
    """Minimal DNS record stub."""

    def __init__(self, value: str) -> None:
        """Initialize the stub.

        :param value: Text value returned by ``to_text``.
        :type value: str
        """

        self.value: str = value

    def to_text(self) -> str:
        """Return the record text value.

        :return: Record text.
        :rtype: str
        """

        return self.value


class FakeBackend:
    """Thread-local backend stub."""

    def __init__(
        self,
        handler: Callable[[str, str, str], list[FakeRecord]],
    ) -> None:
        """Initialize the backend.

        :param handler: Callable handling ``resolve`` requests.
        :type handler: collections.abc.Callable
        """

        self.handler: Callable[[str, str, str], list[FakeRecord]] = handler
        self.nameservers: list[str] = []
        self.lifetime: float = 0.0

    def resolve(self, domain: str, qname: str) -> list[FakeRecord]:
        """Handle one fake DNS lookup.

        :param domain: Query domain.
        :type domain: str
        :param qname: Record type.
        :type qname: str
        :return: Fake answer records.
        :rtype: list[FakeRecord]
        """

        return self.handler(domain, qname, self.nameservers[0])


def build_resolver(
    config: ResolverConfig,
    handler: Callable[[str, str, str], list[FakeRecord]],
) -> DnsResolver:
    """Build a resolver with the fake backend.

    :param config: Resolver config.
    :type config: ResolverConfig
    :param handler: Fake backend handler.
    :type handler: collections.abc.Callable
    :return: Configured resolver.
    :rtype: DnsResolver
    """

    return DnsResolver(
        config=config,
        backend_factory=lambda: FakeBackend(handler),
        dns_exception_type=FakeDnsException,
    )


def test_query_uses_explicit_nameserver() -> None:
    """The compatibility ``query`` API should honor an explicit nameserver."""

    captured_nameservers: list[str] = []

    def handler(domain: str, qname: str, nameserver: str) -> list[FakeRecord]:
        captured_nameservers.append(nameserver)
        return [FakeRecord(f"{domain}:{qname}:{nameserver}")]

    resolver = build_resolver(
        ResolverConfig(nameservers=["ns-1"], tries_per_nameserver=1, max_workers=1),
        handler,
    )

    answer = resolver.query("example.com", "ns-2")

    assert [record.to_text() for record in answer] == ["example.com:A:ns-2"]
    assert captured_nameservers == ["ns-2"]


def test_resolve_queries_each_nameserver_for_each_try() -> None:
    """High-coverage resolution should fan out across nameservers and tries."""

    counts: dict[tuple[str, str], int] = {}
    lock = threading.Lock()

    def handler(domain: str, qname: str, nameserver: str) -> list[FakeRecord]:
        assert qname == "A"
        with lock:
            counts[(domain, nameserver)] = counts.get((domain, nameserver), 0) + 1
        return [FakeRecord(f"{domain}-{nameserver}")]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1", "ns-2"],
            tries_per_nameserver=3,
            max_workers=2,
        ),
        handler,
    )

    result = resolver.resolve(["example.com"])

    assert result == {"example.com": {"example.com-ns-1", "example.com-ns-2"}}
    assert counts == {
        ("example.com", "ns-1"): 3,
        ("example.com", "ns-2"): 3,
    }


def test_resolve_supports_www_variants() -> None:
    """The resolver should preserve the legacy ``www`` expansion behavior."""

    def handler(domain: str, _qname: str, nameserver: str) -> list[FakeRecord]:
        return [FakeRecord(f"{domain}-{nameserver}")]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1"],
            tries_per_nameserver=1,
            max_workers=1,
            www=True,
        ),
        handler,
    )

    result = resolver.resolve(["example.com"])

    assert result == {
        "example.com": {"example.com-ns-1"},
        "www.example.com": {"www.example.com-ns-1"},
    }


def test_resolve_combines_www_results() -> None:
    """The resolver should combine ``www`` and non-``www`` results when enabled."""

    def handler(domain: str, _qname: str, _nameserver: str) -> list[FakeRecord]:
        return [FakeRecord(domain)]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1"],
            tries_per_nameserver=1,
            max_workers=1,
            www_combine=True,
        ),
        handler,
    )

    result = resolver.resolve(["example.com", "www.example.com"])

    assert result == {"example.com": {"example.com", "www.example.com"}}


def test_resolve_verbose_collects_errors() -> None:
    """Verbose mode should expose per-nameserver exceptions."""

    def handler(_domain: str, _qname: str, nameserver: str) -> list[FakeRecord]:
        if nameserver == "ns-2":
            raise FakeDnsException("boom")
        return [FakeRecord("1.1.1.1")]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1", "ns-2"],
            tries_per_nameserver=1,
            max_workers=2,
            verbose=True,
        ),
        handler,
    )

    result = cast(dict[str, Any], resolver.resolve(["example.com"]))

    assert result["success"] == {"example.com": {"1.1.1.1"}}
    assert isinstance(result["error"]["example.com"]["ns-2"], FakeDnsException)


def test_resolve_text_uses_bounded_concurrency() -> None:
    """Bulk resolution should not exceed the configured worker limit."""

    active = 0
    max_active = 0
    lock = threading.Lock()

    def handler(domain: str, _qname: str, nameserver: str) -> list[FakeRecord]:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return [FakeRecord(f"{domain}-{nameserver}")]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1", "ns-2", "ns-3"],
            tries_per_nameserver=1,
            max_workers=2,
        ),
        handler,
    )

    result = resolver.resolve_many_text(["example.com", "example.net"])

    assert result["example.com"] == [
        "example.com-ns-1",
        "example.com-ns-2",
        "example.com-ns-3",
    ]
    assert result["example.net"] == [
        "example.net-ns-1",
        "example.net-ns-2",
        "example.net-ns-3",
    ]
    assert max_active <= 2


def test_resolve_text_reuses_prefetch_cache() -> None:
    """Per-run prefetch results should be reused by subsequent lookups."""

    calls: list[str] = []

    def handler(domain: str, _qname: str, nameserver: str) -> list[FakeRecord]:
        calls.append(f"{domain}:{nameserver}")
        return [FakeRecord("1.1.1.1")]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1"],
            tries_per_nameserver=1,
            max_workers=1,
        ),
        handler,
    )

    resolver.prefetch(["example.com"])
    first = resolver.resolve_text("example.com")
    second = resolver.resolve_text("example.com")

    assert first == ["1.1.1.1"]
    assert second == ["1.1.1.1"]
    assert calls == ["example.com:ns-1"]


def test_resolve_text_raises_for_missing_domain() -> None:
    """Failed domains should raise when no answers are found."""

    def handler(_domain: str, _qname: str, _nameserver: str) -> list[FakeRecord]:
        raise FakeDnsException("nxdomain")

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1"],
            tries_per_nameserver=1,
            max_workers=1,
            verbose=True,
        ),
        handler,
    )

    with pytest.raises(RuntimeError, match="Could not resolve example.com"):
        resolver.resolve_text("example.com")


def test_resolve_text_preserves_errors_when_verbose_is_disabled() -> None:
    """Direct text resolution should keep backend error details without verbose mode."""

    def handler(_domain: str, _qname: str, _nameserver: str) -> list[FakeRecord]:
        raise FakeDnsException("boom")

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1"],
            tries_per_nameserver=1,
            max_workers=1,
            verbose=False,
        ),
        handler,
    )

    with pytest.raises(DomainResolutionError, match="ns-1: boom") as error_info:
        resolver.resolve_text("example.com")

    assert isinstance(error_info.value.errors["ns-1"], FakeDnsException)


def test_prefetch_failure_does_not_poison_later_retry() -> None:
    """A failed prefetch should not suppress a later successful retry."""

    state: dict[str, int] = {"calls": 0}

    def handler(_domain: str, _qname: str, _nameserver: str) -> list[FakeRecord]:
        state["calls"] += 1
        if state["calls"] == 1:
            raise FakeDnsException("transient")
        return [FakeRecord("1.2.3.4")]

    resolver = build_resolver(
        ResolverConfig(
            nameservers=["ns-1"],
            tries_per_nameserver=1,
            max_workers=1,
        ),
        handler,
    )

    resolver.prefetch(["example.com"])

    assert resolver.resolve_text("example.com") == ["1.2.3.4"]
    assert state["calls"] == 2

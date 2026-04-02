from __future__ import annotations

"""Base plugin utilities for nftables set element generation."""

from argparse import Namespace
from ipaddress import IPv4Address
import json
import logging
from pathlib import Path
from typing import Any

import datelib
from dns_resolver import DnsResolver
from file_retriever import FileRetriever


CACHE_DIR_DEFAULT = Path("/tmp")
CACHE_DURATION_DEFAULT = 86400


class Plugin:
    """Base class for all set element plugins."""

    def __init__(
        self,
        metadata: dict[str, Any],
        resolver: DnsResolver | None,
        logger: logging.Logger,
        config: dict[str, Any],
        args: Namespace,
    ) -> None:
        """Initialize the plugin.

        :param metadata: Per-set plugin metadata.
        :type metadata: dict[str, Any]
        :param resolver: Shared DNS resolver.
        :type resolver: DnsResolver | None
        :param logger: Plugin logger.
        :type logger: logging.Logger
        :param config: Full application configuration.
        :type config: dict[str, Any]
        :param args: Parsed command line arguments.
        :type args: argparse.Namespace
        """

        self.metadata = metadata
        self.resolver = resolver
        self.logger = logger
        self.config = config
        self.args = args
        self.cache_dir = Path(metadata.get("cache_dir", CACHE_DIR_DEFAULT))
        self.cache_duration = int(metadata.get("cache_duration", CACHE_DURATION_DEFAULT))

    def collect_hostnames(self) -> set[str]:
        """Return hostnames this plugin intends to resolve.

        :return: Hostnames for optional manager prefetch.
        :rtype: set[str]
        """

        return set()

    @staticmethod
    def is_ipv4_address(hostname: str) -> bool:
        """Return whether ``hostname`` is a valid IPv4 address.

        :param hostname: Value to validate.
        :type hostname: str
        :return: ``True`` for valid IPv4 addresses.
        :rtype: bool
        """

        try:
            IPv4Address(hostname)
        except ValueError:
            return False
        return True

    def cache_ips(self) -> bool:
        """Return whether persistent IP cache retention is enabled.

        :return: ``True`` when cache retention is active.
        :rtype: bool
        """

        return self.cache_duration > 0

    def rebuild_cached_ips(self, filename: str, ips: list[str]) -> list[str]:
        """Merge fresh IPs with unexpired cached IPs for one hostname.

        :param filename: Cache key for the hostname.
        :type filename: str
        :param ips: Fresh IP results.
        :type ips: list[str]
        :return: Combined sorted IPs.
        :rtype: list[str]
        """

        self.logger.debug("Fetching cached IPs for %s, new IPs: %s", filename, ips)
        cache_file = self.cache_dir / f"{filename}.cached.json"
        file_retriever = FileRetriever(self.logger, str(cache_file), str(cache_file))
        cached_ips = file_retriever.get_json() or {}
        current_iso_date = datelib.current_iso_date()
        expiry_threshold = datelib.current_unix_timestamp() - self.cache_duration
        self.logger.debug(
            "Previously cached IPs for %s: %s -- duration: %d",
            filename,
            cached_ips,
            self.cache_duration,
        )
        valid_cached_ips = {
            ip_address: timestamp
            for ip_address, timestamp in cached_ips.items()
            if datelib.iso_utc_date_2epoch(timestamp) > expiry_threshold
        }
        for ip_address in ips:
            valid_cached_ips[ip_address] = current_iso_date
        self.logger.debug(
            "Full cache list for %s: %s",
            filename,
            json.dumps(valid_cached_ips, sort_keys=True),
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        file_retriever.write_cache_file(json.dumps(valid_cached_ips, indent=2, sort_keys=True))
        return sorted(valid_cached_ips)

    def resolve_hostname_ips(self, hostname: str, cache_key: str | None = None) -> list[str]:
        """Resolve one hostname to IPv4 text answers.

        :param hostname: Hostname or IPv4 address to resolve.
        :type hostname: str
        :param cache_key: Optional cache key used for IP retention.
        :type cache_key: str | None
        :return: IPv4 addresses for the hostname.
        :rtype: list[str]
        :raises RuntimeError: If no resolver is available.
        """

        if self.is_ipv4_address(hostname):
            ips = [hostname]
        else:
            if self.resolver is None:
                raise RuntimeError("DNS resolver is not configured")
            ips = self.resolver.resolve_text(hostname)
        if self.cache_ips():
            return self.rebuild_cached_ips(cache_key or hostname, ips)
        return sorted(dict.fromkeys(ips))

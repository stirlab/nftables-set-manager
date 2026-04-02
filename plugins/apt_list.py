from __future__ import annotations

"""Plugin for resolving hostnames referenced by APT source lists."""

from argparse import Namespace
from logging import Logger
from typing import Any
from urllib.parse import urlparse

from dns_resolver import DnsResolver
from plugins import Plugin


class GetElements(Plugin):
    """Resolve unique APT repository hostnames to IPv4 addresses."""

    def __init__(
        self,
        metadata: dict[str, Any],
        resolver: DnsResolver | None,
        logger: Logger,
        config: dict[str, Any],
        args: Namespace,
    ) -> None:
        """Initialize the plugin.

        :param metadata: Per-set metadata.
        :type metadata: dict[str, Any]
        :param resolver: Shared DNS resolver.
        :type resolver: DnsResolver | None
        :param logger: Plugin logger.
        :type logger: logging.Logger
        :param config: Full application config.
        :type config: dict[str, Any]
        :param args: Parsed command line args.
        :type args: argparse.Namespace
        """

        super().__init__(metadata, resolver, logger, config, args)
        self.ignore_missing_hosts = bool(metadata.get("ignore_missing_hosts", False))
        self.ignore_hosts = {str(hostname) for hostname in metadata.get("ignore_hosts", [])}
        self.additional_hosts = [str(hostname) for hostname in metadata.get("additional_hosts", [])]

    def collect_hostnames(self) -> set[str]:
        """Return APT and additional hostnames for manager prefetch.

        :return: Hostnames needing DNS resolution.
        :rtype: set[str]
        """

        return {
            hostname
            for hostname in self.get_candidate_hosts()
            if hostname not in self.ignore_hosts and not self.is_ipv4_address(hostname)
        }

    def get_elements(self) -> list[str]:
        """Resolve all relevant APT hostnames.

        :return: IPv4 set elements.
        :rtype: list[str]
        """

        elements: list[str] = []
        hostnames = sorted(
            {
                hostname
                for hostname in self.get_candidate_hosts()
                if hostname not in self.ignore_hosts
            },
        )
        for hostname in hostnames:
            self.logger.debug("Looking up IPs for hostname: %s", hostname)
            try:
                ips = self.resolve_hostname_ips(hostname)
                self.logger.debug("Retrieved IPs for hostname %s: %s", hostname, ips)
                elements.extend(ips)
            except Exception as error:
                if self.ignore_missing_hosts:
                    continue
                raise RuntimeError(
                    f"Could not retrieve IPs for hostname {hostname}: {error}",
                ) from error
        return sorted(dict.fromkeys(elements))

    def get_unique_hosts_from_apt_list(self) -> list[str]:
        """Parse unique HTTP(S) hosts from the local APT sources list.

        :return: Unique APT hostnames.
        :rtype: list[str]
        """

        from aptsources.sourceslist import SourcesList

        sources_list = SourcesList()
        sources_list.refresh()
        hosts: list[str] = []
        for source in sources_list:
            if source.uri.startswith("http"):
                hostname = urlparse(source.uri).netloc
                if hostname and hostname not in hosts:
                    hosts.append(hostname)
        self.logger.debug("Parsed unique hosts from apt lists: %s", hosts)
        return hosts

    def get_candidate_hosts(self) -> list[str]:
        """Return all host candidates that can become final set elements.

        :return: Ordered unique host candidates.
        :rtype: list[str]
        """

        candidates = self.get_unique_hosts_from_apt_list() + self.additional_hosts
        return list(dict.fromkeys(candidates))

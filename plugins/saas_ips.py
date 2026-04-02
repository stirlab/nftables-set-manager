from __future__ import annotations

"""Plugin for resolving fixed SaaS hostnames to IPv4 addresses."""

from argparse import Namespace
from logging import Logger
from typing import Any

from dns_resolver import DnsResolver
from plugins import Plugin


SAAS_HOSTNAMES = [
    "spaas.drbd.io",
]


class GetElements(Plugin):
    """Resolve fixed SaaS hostnames into nftables set elements."""

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

    def collect_hostnames(self) -> set[str]:
        """Return fixed SaaS hostnames for manager prefetch.

        :return: Hostnames needing DNS resolution.
        :rtype: set[str]
        """

        return set(SAAS_HOSTNAMES)

    def get_elements(self) -> list[str]:
        """Resolve fixed SaaS hostnames.

        :return: IPv4 set elements.
        :rtype: list[str]
        """

        elements: list[str] = []
        for hostname in SAAS_HOSTNAMES:
            self.logger.debug("Looking up IPs for hostname: %s", hostname)
            try:
                elements.extend(self.resolve_hostname_ips(hostname))
            except Exception as error:
                self.logger.error(
                    "Could not retrieve IPs for hostname %s: %s",
                    hostname,
                    error,
                )
        return sorted(dict.fromkeys(elements))

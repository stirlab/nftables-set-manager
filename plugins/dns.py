from __future__ import annotations

"""Plugin for resolving configured hostnames to IPv4 addresses."""

from typing import Any

from plugins import Plugin


class GetElements(Plugin):
    """Resolve configured hostnames into nftables set elements."""

    def __init__(
        self,
        metadata: dict[str, Any],
        resolver: Any,
        logger: Any,
        config: dict[str, Any],
        args: Any,
    ) -> None:
        """Initialize the plugin.

        :param metadata: Per-set metadata.
        :type metadata: dict[str, Any]
        :param resolver: Shared DNS resolver.
        :type resolver: Any
        :param logger: Plugin logger.
        :type logger: Any
        :param config: Full application config.
        :type config: dict[str, Any]
        :param args: Parsed command line args.
        :type args: Any
        """

        super().__init__(metadata, resolver, logger, config, args)
        self.ignore_missing_hosts = bool(metadata.get("ignore_missing_hosts", False))
        self.hostnames = [str(hostname) for hostname in metadata.get("hostnames", [])]

    def collect_hostnames(self) -> set[str]:
        """Return hostnames for manager prefetch.

        :return: Hostnames needing DNS resolution.
        :rtype: set[str]
        """

        return {hostname for hostname in self.hostnames if not self.is_ipv4_address(hostname)}

    def get_elements(self) -> list[str]:
        """Resolve configured hostnames into IPv4 elements.

        :return: IPv4 set elements.
        :rtype: list[str]
        """

        elements: list[str] = []
        for hostname in self.hostnames:
            self.logger.debug("Looking up IPs for hostname: %s", hostname)
            try:
                elements.extend(self.resolve_hostname_ips(hostname))
            except Exception as error:
                if self.ignore_missing_hosts:
                    continue
                raise RuntimeError(
                    f"Could not retrieve IPs for hostname {hostname}: {error}",
                ) from error
        return sorted(dict.fromkeys(elements))

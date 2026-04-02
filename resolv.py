from __future__ import annotations

"""Helpers for reading nameserver IPs from resolver configuration."""

from argparse import Namespace
from ipaddress import IPv4Address
import logging
from pathlib import Path
from typing import Any


RESOLV_DEFAULT = Path("/etc/resolv.conf")


class Resolv:
    """Extract nameserver IPs from a resolver configuration file."""

    def __init__(
        self,
        logger: logging.Logger,
        config: dict[str, Any],
        args: Namespace,
    ) -> None:
        """Initialize the resolver config reader.

        :param logger: Logger instance.
        :type logger: logging.Logger
        :param config: Full application config.
        :type config: dict[str, Any]
        :param args: Parsed command line args.
        :type args: argparse.Namespace
        """

        self.logger = logger
        self.config = config
        self.args = args
        self.resolv_file = Path(config.get("resolv_file", RESOLV_DEFAULT))

    def get_elements(self) -> list[str]:
        """Return nameserver IPv4 addresses.

        :return: Nameserver IPv4 addresses.
        :rtype: list[str]
        """

        return self.get_unix_dns_ips()

    def get_unix_dns_ips(self) -> list[str]:
        """Parse IPv4 nameservers from the configured ``resolv.conf`` file.

        :return: Unique IPv4 nameserver addresses.
        :rtype: list[str]
        """

        self.logger.debug("Parsing %s for nameservers", self.resolv_file)
        dns_ips: list[str] = []
        with self.resolv_file.open("r", encoding="utf-8") as resolv_stream:
            for line in resolv_stream:
                columns = line.split()
                if len(columns) < 2 or columns[0] != "nameserver":
                    continue
                ip_address = columns[1]
                if self.is_valid_ipv4_address(ip_address) and ip_address not in dns_ips:
                    self.logger.debug("Found DNS IP: %s", ip_address)
                    dns_ips.append(ip_address)
        return dns_ips

    @staticmethod
    def is_valid_ipv4_address(address: str) -> bool:
        """Return whether ``address`` is a valid IPv4 address.

        :param address: Address to validate.
        :type address: str
        :return: ``True`` for valid IPv4 addresses.
        :rtype: bool
        """

        try:
            IPv4Address(address)
        except ValueError:
            return False
        return True

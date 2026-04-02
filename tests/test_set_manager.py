"""Integration-focused tests for manager and plugin wiring."""

from __future__ import annotations

from argparse import Namespace
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from pytest import LogCaptureFixture, MonkeyPatch

# pyright: reportImplicitRelativeImport=false
from plugins.apt_list import GetElements as AptListPlugin
from plugins.dns import GetElements as DnsPlugin
from set_manager import SetManager


class FakeResolver:
    """Resolver stub used by manager and plugin tests."""

    instances: list["FakeResolver"] = []

    def __init__(self, config: object, logger: logging.Logger) -> None:
        """Initialize the resolver stub.

        :param config: Resolver configuration.
        :type config: object
        :param logger: Logger instance.
        :type logger: logging.Logger
        """

        self.config: object = config
        self.logger: logging.Logger = logger
        self.prefetch_calls: list[list[str]] = []
        self.resolved_domains: list[str] = []
        self.query_calls: list[str] = []
        type(self).instances.append(self)

    def prefetch(self, domains: list[str]) -> None:
        """Record one prefetch call.

        :param domains: Domains being prefetched.
        :type domains: list[str]
        """

        self.prefetch_calls.append(list(domains))

    def resolve_text(self, domain: str) -> list[str]:
        """Return a deterministic IPv4 for a domain.

        :param domain: Domain to resolve.
        :type domain: str
        :return: Fake IPv4 answers.
        :rtype: list[str]
        """

        self.resolved_domains.append(domain)
        suffix = len(self.resolved_domains)
        return [f"10.0.0.{suffix}"]

    def query(
        self,
        domain: str,
        _nameserver: str | None = None,
    ) -> list[SimpleNamespace]:
        """Return a fake compatibility answer object.

        :param domain: Domain to resolve.
        :type domain: str
        :param nameserver: Optional nameserver.
        :type nameserver: str | None
        :return: Fake answer record list.
        :rtype: list[types.SimpleNamespace]
        """

        self.query_calls.append(domain)
        return [SimpleNamespace(to_text=lambda: "10.0.0.99")]


class FakeResolv:
    """System resolver config stub."""

    def __init__(
        self,
        logger: logging.Logger,
        config: dict[str, object],
        args: Namespace,
    ) -> None:
        """Initialize the stub.

        :param logger: Logger instance.
        :type logger: logging.Logger
        :param config: Application config.
        :type config: dict[str, object]
        :param args: Parsed args.
        :type args: argparse.Namespace
        """

        self.logger: logging.Logger = logger

    def get_elements(self) -> list[str]:
        """Return fake nameserver IPs.

        :return: Fake nameservers.
        :rtype: list[str]
        """

        return ["192.0.2.53"]


class FakeNftablesSet:
    """In-memory nftables set stub."""

    def __init__(self, args: Namespace, config: dict[str, object]) -> None:
        """Initialize the stub.

        :param args: Parsed args.
        :type args: argparse.Namespace
        :param config: Application config.
        :type config: dict[str, object]
        """

        self.elements: dict[str, list[str]] = {}

    def set_operation(
        self,
        op: str,
        _set_family: str,
        _set_table: str,
        set_name: str,
        elements: list[str] | None = None,
    ) -> None:
        """Apply a fake nftables operation.

        :param op: Operation name.
        :type op: str
        :param set_family: Set family.
        :type set_family: str
        :param set_table: Set table.
        :type set_table: str
        :param set_name: Set name.
        :type set_name: str
        :param elements: Optional elements.
        :type elements: list[str] | None
        """

        current = self.elements.setdefault(set_name, [])
        if op == "flush":
            self.elements[set_name] = []
            return
        if elements is None:
            return
        if op == "add":
            self.elements[set_name] = sorted(dict.fromkeys(current + elements))
        if op == "delete":
            self.elements[set_name] = [item for item in current if item not in elements]

    def get_set_elements(
        self,
        _set_family: str,
        _set_table: str,
        set_name: str,
    ) -> list[str]:
        """Return stored set elements.

        :param set_family: Set family.
        :type set_family: str
        :param set_table: Set table.
        :type set_table: str
        :param set_name: Set name.
        :type set_name: str
        :return: Stored elements.
        :rtype: list[str]
        """

        return list(self.elements.get(set_name, []))


def build_args(plugin_dir: Path) -> Namespace:
    """Build a minimal argument namespace for tests.

    :param plugin_dir: Plugin directory path.
    :type plugin_dir: pathlib.Path
    :return: Parsed-args equivalent object.
    :rtype: argparse.Namespace
    """

    return Namespace(
        berserk=False,
        config_file="config.yaml",
        debug=False,
        plugin_dir=str(plugin_dir),
        quiet=False,
        sets=None,
    )


def build_config() -> dict[str, object]:
    """Build a minimal manager config for tests.

    :return: Test config.
    :rtype: dict[str, object]
    """

    return {
        "dns_ips_set_name": "dns_ips",
        "sets": {
            "dns_ips": {
                "family": "inet",
                "plugin": "dns",
                "strategy": "replace",
                "table": "filter",
            },
            "app_one": {
                "family": "inet",
                "metadata": {"hostnames": ["one.example.com", "shared.example.com"]},
                "plugin": "dns",
                "strategy": "replace",
                "table": "filter",
            },
            "app_two": {
                "family": "inet",
                "metadata": {"hostnames": ["two.example.com", "shared.example.com"]},
                "plugin": "dns",
                "strategy": "replace",
                "table": "filter",
            },
        },
    }


def test_set_manager_prefetches_shared_dns_hostnames(monkeypatch: MonkeyPatch) -> None:
    """The manager should prefetch shared DNS hosts once per run."""

    FakeResolver.instances = []
    monkeypatch.setattr("set_manager.DnsResolver", FakeResolver)
    monkeypatch.setattr("set_manager.Resolv", FakeResolv)
    monkeypatch.setattr("set_manager.NftablesSet", FakeNftablesSet)

    manager = SetManager(build_args(Path("plugins")), build_config())

    manager.update_sets()

    resolver = FakeResolver.instances[0]
    assert resolver.prefetch_calls == [[
        "one.example.com",
        "shared.example.com",
        "two.example.com",
    ]]
    assert resolver.resolved_domains == [
        "one.example.com",
        "shared.example.com",
        "two.example.com",
        "shared.example.com",
    ]


def test_dns_plugin_reuses_persistent_ip_cache(tmp_path: Path) -> None:
    """The DNS plugin should retain unexpired cached IPs across runs."""

    class CacheResolver:
        """Resolver stub returning a configurable response."""

        def __init__(self, response: list[str]) -> None:
            """Initialize the resolver stub.

            :param response: IPv4 response list.
            :type response: list[str]
            """

            self.response: list[str] = response

        def resolve_text(self, domain: str) -> list[str]:
            """Return the configured response.

            :param domain: Domain to resolve.
            :type domain: str
            :return: IPv4 answers.
            :rtype: list[str]
            """

            _ = domain
            return list(self.response)

    metadata = {
        "cache_dir": str(tmp_path),
        "cache_duration": 3600,
        "hostnames": ["example.com"],
    }
    logger = logging.getLogger("test-plugin-cache")

    first_plugin = DnsPlugin(
        metadata,
        CacheResolver(["10.0.0.1"]),
        logger,
        {},
        Namespace(debug=False, quiet=False),
    )
    second_plugin = DnsPlugin(
        metadata,
        CacheResolver(["10.0.0.2"]),
        logger,
        {},
        Namespace(debug=False, quiet=False),
    )

    first_result = first_plugin.get_elements()
    second_result = second_plugin.get_elements()

    assert first_result == ["10.0.0.1"]
    assert second_result == ["10.0.0.1", "10.0.0.2"]


def test_custom_plugin_can_keep_using_query_api(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """External plugins using ``resolver.query`` should remain compatible."""

    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "legacy_query.py"
    plugin_path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "class GetElements:",
                "    def __init__(self, metadata, resolver, logger, config, args):",
                "        self.resolver = resolver",
                "    def get_elements(self):",
                "        return [record.to_text() for record in self.resolver.query('legacy.example.com')]",
            ],
        ),
        encoding="utf-8",
    )

    FakeResolver.instances = []
    monkeypatch.setattr("set_manager.DnsResolver", FakeResolver)
    monkeypatch.setattr("set_manager.Resolv", FakeResolv)
    monkeypatch.setattr("set_manager.NftablesSet", FakeNftablesSet)

    config = {
        "dns_ips_set_name": "dns_ips",
        "sets": {
            "dns_ips": {
                "family": "inet",
                "plugin": "legacy_query",
                "strategy": "replace",
                "table": "filter",
            },
            "legacy": {
                "family": "inet",
                "plugin": "legacy_query",
                "strategy": "replace",
                "table": "filter",
            },
        },
    }

    manager = SetManager(build_args(plugin_dir), config)

    manager.update_sets()

    resolver = FakeResolver.instances[0]
    assert resolver.query_calls == ["legacy.example.com"]


def test_set_manager_populates_legacy_berserker_ips_default() -> None:
    """Legacy plugins should still see ``berserker_ips`` in config."""

    manager = SetManager(build_args(Path("plugins")), build_config())

    assert manager.config["berserker_ips"] == [
        "8.8.8.8",
        "8.8.4.4",
        "1.1.1.1",
        "1.0.0.1",
        "9.9.9.9",
    ]


def test_apt_list_keeps_ipv4_literals_in_final_elements(monkeypatch: MonkeyPatch) -> None:
    """APT plugin should exclude IPv4 literals from prefetch but keep them in output."""

    FakeResolver.instances = []
    resolver = FakeResolver(None, logging.getLogger("test-resolver"))
    def fake_hosts(_self: AptListPlugin) -> list[str]:
        return ["198.51.100.10", "packages.example.com"]

    monkeypatch.setattr(AptListPlugin, "get_unique_hosts_from_apt_list", fake_hosts)

    plugin = AptListPlugin(
        {"additional_hosts": ["203.0.113.20"]},
        cast(Any, resolver),
        logging.getLogger("test-apt-list"),
        {},
        Namespace(debug=False, quiet=False),
    )

    assert plugin.collect_hostnames() == {"packages.example.com"}
    assert plugin.get_elements() == ["10.0.0.1", "198.51.100.10", "203.0.113.20"]


def test_update_set_distinguishes_plugin_skip_from_failure(
    caplog: LogCaptureFixture,
) -> None:
    """Manager logging should keep plugin skip and failure distinct."""

    manager = SetManager(build_args(Path("plugins")), build_config())
    manager.nftables_set = cast(Any, FakeNftablesSet(Namespace(), {}))

    with caplog.at_level(logging.INFO):
        manager.update_set("app_one", False)
        manager.update_set("app_one", None)

    assert "returned without updating elements" in caplog.text
    assert "failed to produce elements" in caplog.text

#!/usr/bin/env python3

from __future__ import annotations

"""Command-line entrypoint for nftables set management."""

import argparse
import logging
from pathlib import Path
import sys
from typing import Any

import yaml

from set_manager import SetManager


DEFAULT_SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_FILE = DEFAULT_SCRIPT_DIR / "config.yaml"
DEFAULT_PLUGIN_DIR = DEFAULT_SCRIPT_DIR / "plugins"


class ManageSetsApplication:
    """CLI application for nftables set management."""

    def __init__(self) -> None:
        """Initialize the CLI application."""

        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, argv: list[str] | None = None) -> int:
        """Run the CLI application.

        :param argv: Optional CLI argument vector.
        :type argv: list[str] | None
        :return: Exit code.
        :rtype: int
        """

        args = self.parse_args(argv)
        self.configure_logging(args.debug, args.quiet)
        try:
            config = self.load_config(Path(args.config_file))
            manager = SetManager(args, config)
            manager.update_sets()
        except Exception as error:
            self.logger.error("%s", error)
            return 1
        return 0

    def parse_args(self, argv: list[str] | None = None) -> argparse.Namespace:
        """Parse command line arguments.

        :param argv: Optional CLI argument vector.
        :type argv: list[str] | None
        :return: Parsed arguments.
        :rtype: argparse.Namespace
        """

        parser = argparse.ArgumentParser(description="Manage nftables sets")
        parser.add_argument(
            "--config-file",
            type=str,
            metavar="FILE",
            default=str(DEFAULT_CONFIG_FILE),
            help="Configuration filepath. Default: %(default)s",
        )
        parser.add_argument(
            "--plugin-dir",
            type=str,
            metavar="DIR",
            default=str(DEFAULT_PLUGIN_DIR),
            help="Directory that contains plugins. Default: %(default)s",
        )
        parser.add_argument(
            "--sets",
            action="store",
            metavar="SET",
            type=str,
            nargs="+",
            help="Sets to update. Default is to update all configured sets.",
        )
        parser.add_argument(
            "--berserk",
            action="store_true",
            help="Add fallback public resolver IPs to the DNS resolver.",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Silence output except for errors",
        )
        return parser.parse_args(argv)

    def configure_logging(self, debug: bool, quiet: bool) -> None:
        """Configure application logging.

        :param debug: Whether debug logging is enabled.
        :type debug: bool
        :param quiet: Whether non-error logging should be suppressed.
        :type quiet: bool
        """

        level = logging.INFO
        if quiet:
            level = logging.ERROR
        if debug:
            level = logging.DEBUG
        logging.basicConfig(level=level)

    def load_config(self, config_file: Path) -> dict[str, Any]:
        """Load the YAML configuration file.

        :param config_file: Config file path.
        :type config_file: pathlib.Path
        :return: Parsed configuration.
        :rtype: dict[str, Any]
        :raises RuntimeError: If the config cannot be loaded.
        """

        try:
            with config_file.open("r", encoding="utf-8") as stream:
                loaded = yaml.safe_load(stream)
        except FileNotFoundError as error:
            raise RuntimeError(f"Config file does not exist: {config_file}") from error
        except yaml.YAMLError as error:
            raise RuntimeError(f"Could not load config file {config_file}: {error}") from error
        if not isinstance(loaded, dict):
            raise RuntimeError(f"Invalid config file {config_file}: expected a mapping")
        return loaded


def main() -> int:
    """Run the CLI application and return an exit code.

    :return: Exit code.
    :rtype: int
    """

    application = ManageSetsApplication()
    return application.run()


if __name__ == "__main__":
    sys.exit(main())

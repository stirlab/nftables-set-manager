#!/usr/bin/env python3

import os
import argparse
import yaml
from set_manager import SetManager

DEFAULT_SCRIPT_DIR = os.path.dirname(__file__)
DEFAULT_CONFIG_FILE = "%s/config.yaml" % DEFAULT_SCRIPT_DIR
DEFAULT_PLUGIN_DIR = "%s/plugins" % DEFAULT_SCRIPT_DIR

def main():
    parser = argparse.ArgumentParser(description="Manage nftables sets")
    parser.add_argument("--debug", action='store_true', help="Enable debugging")
    parser.add_argument("--sets", action='store', metavar="SET", type=str, nargs='+', help="Sets to update. Default is to update all sets in the configuration file")
    parser.add_argument("--config-file", type=str, metavar="FILE", default=DEFAULT_CONFIG_FILE, help="Configuration filepath, default: %s" % DEFAULT_CONFIG_FILE)
    parser.add_argument("--plugin-dir", type=str, metavar="FILE", default=DEFAULT_PLUGIN_DIR, help="Directory that contains plugins, default: %s" % DEFAULT_PLUGIN_DIR)
    args = parser.parse_args()
    with open(args.config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as err:
            raise RuntimeError("Could not load config file %s: %s" % (args.config_file, err))
        manager = SetManager(args, config)
        manager.update_sets()

if __name__ == "__main__":
    main()

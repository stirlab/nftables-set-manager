#!/usr/bin/env python3

from sys import argv
import os
import argparse
import logging
import importlib.util
import yaml
import json

CONFIG_FILE = 'config.yaml'
DEFAULT_PLUGIN_DIR_NAME = 'plugins'
DEFAULT_SCRIPT_DIR = os.path.dirname(__file__)
logging.basicConfig(level=logging.INFO)

class SetManager(object):

    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.sets = self.args.sets
        self.script_dir = DEFAULT_SCRIPT_DIR
        self.plugin_dir_name = DEFAULT_PLUGIN_DIR_NAME
        self.plugin_dir = '%s/%s' % (self.script_dir, self.plugin_dir_name)
        self.plugin_cache = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)

    def load_plugin(self, plugin):
        if plugin not in self.plugin_cache:
            module = '%s.%s' % (self.plugin_dir, plugin)
            filepath = '%s/%s/%s.py' % (self.script_dir, self.plugin_dir, plugin)
            try:
                spec = importlib.util.spec_from_file_location(module, filepath)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except SyntaxError as e:
                raise SyntaxError("Plugin: %s (%s) -- %s" % (plugin, filepath, e))
            except:
                raise RuntimeError("Plugin: %s (%s) -- %s" % (plugin, filepath, e))
            plugin_logger = logging.getLogger('plugin:%s' % plugin)
            plugin_logger.setLevel(self.logger.level)
            self.logger.debug("Caching plugin: %s" % plugin)
            self.plugin_cache[plugin] = {
                'class': getattr(mod, 'GetElements'),
                'logger': plugin_logger,
            }
        return self.plugin_cache[plugin]

    def update_set(self, set_name):
        config = self.config['sets'][set_name]
        self.logger.debug("Updating set '%s' with config: %s" % (set_name, json.dumps(config)))
        plugin = self.load_plugin(config['plugin'])
        metadata = 'metadata' in config and config['metadata'] or {}
        try:
            instance = plugin['class'](plugin['logger'], metadata)
            elements = instance.get_elements()
            self.logger.debug("Got elements for set '%s': %s" % (set_name, json.dumps(elements)))
            return elements
        except Exception as e: # work on python 3.x
            self.logger.error('Failed to get elements for set %s: %s' % (set_name, str(e)))

    def get_all_sets(self):
        return self.config['sets'].keys()

    def update_sets(self):
        if not self.sets:
            self.logger.debug("No sets passed, updating all sets")
            self.sets = self.get_all_sets()
        for _set in self.sets:
            if _set in self.config['sets']:
                self.update_set(_set)
            else:
                raise KeyError("Invalid set: %s" % _set)

def main():
    parser = argparse.ArgumentParser(description="Manage nftables sets")
    parser.add_argument("--debug", action='store_true', help="Enable debugging")
    parser.add_argument("--sets", action='store', type=str, nargs='+', help="Sets to update. Default is to update all sets in %s" % CONFIG_FILE)
    args = parser.parse_args()
    config_file = "%s/%s" % (DEFAULT_SCRIPT_DIR, CONFIG_FILE)
    with open(config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as err:
            raise RuntimeError("Could not load config file %s: %s" % err)
        manager = SetManager(args, config)
        manager.update_sets()

if __name__ == "__main__":
    main()

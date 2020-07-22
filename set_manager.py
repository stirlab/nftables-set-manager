#!/usr/bin/env python3

import os
import logging
import importlib.util
import json
from nftables_set import NftablesSet

logging.basicConfig(level=logging.WARNING)

class SetManager(object):

    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.sets = self.args.sets
        self.plugin_dir = args.plugin_dir
        self.plugin_cache = {}
        self.nftables_set = NftablesSet(self.args, self.config)
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)

    def load_plugin(self, plugin):
        if plugin not in self.plugin_cache:
            filepath = '%s/%s.py' % (self.plugin_dir, plugin)
            try:
                spec = importlib.util.spec_from_file_location(plugin, filepath)
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

    def fetch_set_elements(self, set_name):
        config = self.get_set_config(set_name)
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

    def update_set(self, set_name, elements):
        config = self.get_set_config(set_name)
        if elements is False:
            self.logger.warning('Plugin %s returned without updating elements, skiping update' % config['plugin'])
        if config['strategy'] == 'replace':
            self.nftables_set.set_operation('flush', config['family'], config['table'], set_name)
        if len(elements) > 0:
            self.nftables_set.set_operation('add', config['family'], config['table'], set_name, elements)
        if config['strategy'] == 'update':
            self.remove_expired_elements(set_name, elements)
        final_set = self.nftables_set.get_set_elements(config['family'], config['table'], set_name)
        self.logger.debug("Final values for set %s: %s" % (set_name, json.dumps(final_set)))

    def remove_expired_elements(self, set_name, elements):
        config = self.get_set_config(set_name)
        self.logger.debug("Replace strategy for set %s, removing old elements" % set_name)
        current_set = set(self.nftables_set.get_set_elements(config['family'], config['table'], set_name))
        new_set = set(elements)
        to_remove = list(current_set.difference(new_set))
        if len(to_remove) > 0:
            self.nftables_set.set_operation('delete', config['family'], config['table'], set_name, to_remove)

    def get_set_config(self, set_name):
        return self.config['sets'][set_name]

    def get_all_sets(self):
        return self.config['sets'].keys()

    def update_sets(self):
        if not self.sets:
            self.logger.debug("No sets passed, updating all sets")
            self.sets = self.get_all_sets()
        for set_name in self.sets:
            if set_name in self.config['sets']:
                elements = self.fetch_set_elements(set_name)
                self.update_set(set_name, elements)
            else:
                raise KeyError("Invalid set: %s" % set_name)

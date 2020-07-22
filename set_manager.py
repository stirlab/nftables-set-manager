#!/usr/bin/env python3

import os
import logging
import importlib.util
import json

logging.basicConfig(level=logging.WARNING)

class SetManager(object):

    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.sets = self.args.sets
        self.plugin_dir = args.plugin_dir
        self.plugin_cache = {}
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

#!/usr/bin/env python3

from sys import argv
import os
import argparse
import yaml
import json
import logging
import importlib.util

CONFIG_FILE='config.yaml'
PLUGIN_DIR='plugins'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

script_dir = os.path.dirname(__file__)
plugin_dir = '%s/%s' % (script_dir, PLUGIN_DIR)




def load_plugin(plugin):
    module = '%s.%s' % (PLUGIN_DIR, plugin)
    filepath = '%s/%s/%s.py' % (script_dir, PLUGIN_DIR, plugin)
    try:
        spec = importlib.util.spec_from_file_location(module, filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except SyntaxError as e:
        raise SyntaxError("Plugin: %s (%s) -- %s" % (plugin, filepath, e))
    except:
        return None
    return getattr(mod, 'GetElements')

def update_set(set_name, config):
    logger.debug("Updating set '%s' with config: %s" % (set_name, json.dumps(config)))
    klass = load_plugin(config['plugin'])
    metadata = 'metadata' in config and config['metadata'] or {}
    if klass:
        try:
            instance = klass(logger, metadata)
            elements = instance.get_elements()
            logger.debug("Got elements for set '%s': %s" % (set_name, json.dumps(elements)))
            return elements
        except Exception as e: # work on python 3.x
            logger.error('Failed to get elements for set %s: %s' % (set_name, str(e)))
    else:
        logger.error("Could not load plugin: %s" % plugin)
        return None

def update_sets(config, sets):
    if not sets:
        logger.debug("No sets passed, updating all sets")
        sets = config['sets'].keys()
    for _set in sets:
        if _set in config['sets']:
            update_set(_set, config['sets'][_set])
        else:
            raise KeyError("Invalid set: %s" % _set)

def main():
    parser = argparse.ArgumentParser(description="Manage nftables sets")
    parser.add_argument("--debug", action='store_true', help="Enable debugging")
    parser.add_argument("--sets", action='store', type=str, nargs='+', help="Sets to update. Default is to update all sets in %s" % CONFIG_FILE)
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    with open("%s/%s" % (script_dir, CONFIG_FILE), 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as err:
            logger.error(err)
        update_sets(config, args.sets)

if __name__ == "__main__":
    main()

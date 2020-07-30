import sys
import json
import requests
from requests.exceptions import HTTPError
from file_util import cache_file_get, cache_file_write

sys.path.append('..')

# NOTE: Github has some ridiculous DNS variation going on, so this plugin
# implements an optional fallback to cache file for the times the IP of
# api.github.com falls out from underneath us.

GITHUB_IP_RANGES_DEFAULT_JSON_URL = 'https://api.github.com/meta'
DEFAULT_CACHE_FILE = '/tmp/github_ip_ranges.json'
IP_TYPES_DEFAULT = [
    'web',
    'api',
    'git',
]

class GetElements(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.json_url = 'json_url' in metadata and metadata['json_url'] or GITHUB_IP_RANGES_DEFAULT_JSON_URL
        self.ip_types = 'ip_types' in metadata and metadata['ip_types'] or IP_TYPES_DEFAULT
        self.cache_json = 'cache_json' in metadata and metadata['cache_json'] or False
        self.cache_json_file = 'cache_json_file' in metadata and metadata['cache_json_file'] or DEFAULT_CACHE_FILE

    def get_elements(self):
        github_ips = self.get_github_ips_for_types()
        return github_ips

    def write_cache_file(self, data):
        if self.cache_json:
            self.logger.info('Caching data to file: %s' % self.cache_json_file)
            cache_file_write(self.cache_json_file, data)

    def try_cache_file(self):
        if self.cache_json:
            self.logger.info('Trying cache file: %s' % self.cache_json_file)
            return cache_file_get(self.cache_json_file)
        return False

    def get_github_ips_for_types(self):
        self.logger.debug("Retrieving JSON data from : %s" % self.json_url)
        try:
            response = requests.get(self.json_url)
            response.raise_for_status()
            data = response.json()
            self.write_cache_file(response.text)
        except Exception as err:
            self.logger.error('Other error occurred: %s' % err)
            data = self.try_cache_file()
            if not data:
                return False
            return False
        return self.build_elements(data)

    def build_elements(self, data):
        elements = []
        for ip_type in data:
            if ip_type in self.ip_types:
                self.logger.debug("Adding elements for IP type: %s" % ip_type)
                for element in data[ip_type]:
                    elements.append(element)
            else:
                self.logger.debug("Skipping IP type: %s" % ip_type)
        return elements

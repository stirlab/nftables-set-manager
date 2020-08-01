import sys
import json
import requests
from file_util import cache_file_get, cache_file_write

sys.path.append('..')

# NOTE: Google has some ridiculous DNS variation going on, so this plugin
# implements an optional fallback to cache file for the times the IP of
# www.gstatic.com falls out from underneath us.

GOOG_DEFAULT_JSON_URL = "https://www.gstatic.com/ipranges/goog.json"
CLOUD_DEFAULT_JSON_URL = "https://www.gstatic.com/ipranges/cloud.json"
DEFAULT_CACHE_GOOG_FILE = '/tmp/google_goog_ip_ranges.json'
DEFAULT_CACHE_CLOUD_FILE = '/tmp/google_cloud_ip_ranges.json'

class GetElements(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.cloud_default_domains_only = 'cloud_default_domains_only' in metadata and metadata['cloud_default_domains_only'] or False
        self.goog_json_url = 'goog_json_url' in metadata and metadata['goog_json_url'] or GOOG_DEFAULT_JSON_URL
        self.cloud_json_url = 'cloud_json_url' in metadata and metadata['cloud_json_url'] or CLOUD_DEFAULT_JSON_URL
        self.cache_json = 'cache_json' in metadata and metadata['cache_json'] or False
        self.cache_json_goog_file = 'cache_json_goog_file' in metadata and metadata['cache_json_goog_file'] or DEFAULT_CACHE_GOOG_FILE
        self.cache_json_cloud_file = 'cache_json_cloud_file' in metadata and metadata['cache_json_cloud_file'] or DEFAULT_CACHE_CLOUD_FILE

    def get_elements(self):
        google_ips = self.get_google_ips()
        return google_ips

    def write_cache_file(self, cache_file, data):
        if self.cache_json:
            self.logger.info('Caching data to file: %s' % cache_file)
            cache_file_write(cache_file, data)

    def try_cache_file(self, cache_file):
        if self.cache_json:
            self.logger.info('Trying cache file: %s' % cache_file)
            return cache_file_get(cache_file)
        return False

    def get_file_data(self, url, cache_file):
        self.logger.debug("Retrieving JSON data from : %s" % url)
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            self.write_cache_file(cache_file, response.text)
        except Exception as err:
            self.logger.error('Other error occurred: %s' % err)
            content = self.try_cache_file(cache_file)
            if content:
                data = json.loads(content)
            else:
                return False
        return data

    def get_google_ips(self):
        goog_json = self.get_file_data(self.goog_json_url, self.cache_json_goog_file)
        cloud_json = self.get_file_data(self.cloud_json_url, self.cache_json_cloud_file)
        if goog_json and cloud_json:
            self.logger.debug('%s published: %s' % (self.goog_json_url, goog_json.get('creationTime')))
            self.logger.debug('%s published: %s' % (self.cloud_json_url, cloud_json.get('creationTime')))
            goog_cidrs = set()
            for e in goog_json['prefixes']:
                cidr = e.get('ipv4Prefix')
                if cidr:
                    goog_cidrs.add(cidr)
            cloud_cidrs = set()
            for e in cloud_json['prefixes']:
                cidr = e.get('ipv4Prefix')
                if cidr:
                    cloud_cidrs.add(cidr)
            if self.cloud_default_domains_only:
                ip_ranges = list(goog_cidrs.difference(cloud_cidrs))
            else:
                ip_ranges = goog_cidrs
            self.logger.debug("IP ranges for Google APIs and services default domains: %s" % json.dumps(ip_ranges))
            return ip_ranges
        else:
            self.logger.error("JSON data not properly loaded")
            return False

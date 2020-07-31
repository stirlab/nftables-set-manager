import sys
import json
import requests
from requests.exceptions import HTTPError
from file_util import cache_file_get, cache_file_write

sys.path.append('..')

# NOTE: AWS has some ridiculous DNS variation going on, so this plugin
# implements an optional fallback to cache file for the times the IP of
# ip-ranges.amazonaws.com falls out from underneath us.

S3_IP_RANGES_DEFAULT_JSON_URL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'
DEFAULT_CACHE_FILE = '/tmp/s3_ip_ranges.json'
REGIONS_DEFAULT = [
    'us-east-1',
]

class GetElements(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.json_url = 'json_url' in metadata and metadata['json_url'] or S3_IP_RANGES_DEFAULT_JSON_URL
        self.regions = 'regions' in metadata and metadata['regions'] or REGIONS_DEFAULT
        self.cache_json = 'cache_json' in metadata and metadata['cache_json'] or False
        self.cache_json_file = 'cache_json_file' in metadata and metadata['cache_json_file'] or DEFAULT_CACHE_FILE

    def get_elements(self):
        s3_ips = self.get_s3_ips_for_regions()
        return s3_ips

    def write_cache_file(self, data):
        if self.cache_json:
            self.logger.info('Caching data to file: %s' % self.cache_json_file)
            cache_file_write(self.cache_json_file, data)

    def try_cache_file(self):
        if self.cache_json:
            self.logger.info('Trying cache file: %s' % self.cache_json_file)
            return cache_file_get(self.cache_json_file)
        return False

    def get_s3_ips_for_regions(self):
        self.logger.debug("Retrieving data from : %s" % self.json_url)
        try:
            response = requests.get(self.json_url)
            response.raise_for_status()
            data = response.json()
            self.write_cache_file(response.text)
        except Exception as err:
            self.logger.error('Other error occurred: %s' % err)
            content = self.try_cache_file()
            if content:
                data = json.loads(content)
            else:
                return False
        return self.build_elements(data)

    def build_elements(self, data):
        self.logger.debug("Adding elements from regions: %s" % json.dumps(self.regions))
        return [obj['ip_prefix'] for obj in data['prefixes'] if not self.regions or obj['region'] in self.regions]

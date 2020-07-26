import json
import requests
from requests.exceptions import HTTPError

S3_IP_RANGES_DEFAULT_JSON_URL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'
REGIONS_DEFAULT = [
    'us-east-1',
]

class GetElements(object):

    def __init__(self, metadata, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.json_url = 'json_url' in metadata and metadata['json_url'] or S3_IP_RANGES_DEFAULT_JSON_URL
        self.regions = 'regions' in metadata and metadata['regions'] or REGIONS_DEFAULT

    def get_elements(self):
        s3_ips = self.get_s3_ips_for_regions()
        return s3_ips

    def get_s3_ips_for_regions(self):
        self.logger.debug("Retrieving data from : %s" % self.json_url)
        try:
            response = requests.get(self.json_url)
            response.raise_for_status()
            data = response.json()
        except HTTPError as http_err:
            self.logger.error('HTTP error occurred: %s' % http_err)
            return False
        except Exception as err:
            self.logger.error('Other error occurred: %s' % err)
            return False
        return self.build_elements(data)

    def build_elements(self, data):
        self.logger.debug("Adding elements from regions: %s" % json.dumps(self.regions))
        return [obj['ip_prefix'] for obj in data['prefixes'] if not self.regions or obj['region'] in self.regions]

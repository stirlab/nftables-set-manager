import json
import requests
from requests.exceptions import HTTPError

S3_IP_RANGES_JSON_URL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'

class GetElements(object):

    def __init__(self, logger, metadata):
        self.logger = logger
        self.metadata = metadata
        self.regions = 'regions' in metadata and metadata['regions'] or None

    def get_elements(self):
        s3_ips = self.get_s3_ips_for_regions()
        return s3_ips

    def get_s3_ips_for_regions(self):
        try:
            response = requests.get(S3_IP_RANGES_JSON_URL)
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
        return [obj['ip_prefix'] for obj in data['prefixes'] if not self.regions or obj['region'] in self.regions]

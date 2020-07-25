import json
import requests
from requests.exceptions import HTTPError

GITHUB_IP_RANGES_DEFAULT_JSON_URL = 'https://api.github.com/meta'
IP_TYPES_DEFAULT = [
    'web',
    'api',
    'git',
]

class GetElements(object):

    def __init__(self, metadata, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.json_url = 'json_url' in metadata and metadata['json_url'] or GITHUB_IP_RANGES_DEFAULT_JSON_URL
        self.ip_types = 'ip_types' in metadata and metadata['ip_types'] or IP_TYPES_DEFAULT

    def get_elements(self):
        github_ips = self.get_github_ips_for_types()
        return github_ips

    def get_github_ips_for_types(self):
        self.logger.debug("Retrieving JSON data from : %s" % self.json_url)
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
        elements = []
        for ip_type in data:
            if ip_type in self.ip_types:
                self.logger.debug("Adding elements for IP type: %s" % ip_type)
                for element in data[ip_type]:
                    elements.append(element)
            else:
                self.logger.debug("Skipping IP type: %s" % ip_type)
        return elements

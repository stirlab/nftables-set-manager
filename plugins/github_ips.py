import json
import requests
from requests.exceptions import HTTPError

GITHUB_IP_RANGES_JSON_URL = 'https://api.github.com/meta'
# TODO: This sucks, but the A record of api.github.com changes so fast that it
# cannot be trusted from a DNS query.
API_IP_RANGES = [
    "192.30.252.0/22",
    "185.199.108.0/22",
    "140.82.112.0/20",
    "13.230.158.120/32",
    "18.179.245.253/32",
    "52.69.239.207/32",
    "13.209.163.61/32",
    "54.180.75.25/32",
    "13.233.76.15/32",
    "13.234.168.60/32",
    "13.250.168.23/32",
    "13.250.94.254/32",
    "54.169.195.247/32",
    "13.236.14.80/32",
    "13.238.54.232/32",
    "52.63.231.178/32",
    "18.229.199.252/32",
    "54.207.47.76/32"
]
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
        self.ip_types = 'ip_types' in metadata and metadata['ip_types'] or IP_TYPES_DEFAULT

    def get_elements(self):
        github_ips = self.get_github_ips_for_types()
        return github_ips

    def get_github_ips_for_types(self):
        self.logger.debug("Retrieving data from : %s" % GITHUB_IP_RANGES_JSON_URL)
        try:
            response = requests.get(GITHUB_IP_RANGES_JSON_URL)
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
        for element in API_IP_RANGES:
            elements.append(element)
        for ip_type in data:
            if ip_type in self.ip_types:
                self.logger.debug("Adding elements for IP type: %s" % ip_type)
                for element in data[ip_type]:
                    elements.append(element)
            else:
                self.logger.debug("Skipping IP type: %s" % ip_type)
        return elements

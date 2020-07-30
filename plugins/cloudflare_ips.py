import requests
from requests.exceptions import HTTPError

CLOUDFLARE_IP_RANGES_DEFAULT_JSON_URL = 'https://www.cloudflare.com/ips-v4'

class GetElements(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.url = 'url' in metadata and metadata['url'] or CLOUDFLARE_IP_RANGES_DEFAULT_JSON_URL

    def get_elements(self):
        cloudflare_ips = self.get_cloudflare_ips_for_types()
        return cloudflare_ips

    def get_cloudflare_ips_for_types(self):
        self.logger.debug("Retrieving JSON data from : %s" % self.url)
        try:
            response = requests.get(self.url)
            response.raise_for_status()
        except HTTPError as http_err:
            self.logger.error('HTTP error occurred: %s' % http_err)
            return False
        except Exception as err:
            self.logger.error('Other error occurred: %s' % err)
            return False
        elements = response.text.split()
        return elements

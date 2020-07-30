import json
import urllib.request

GOOG_DEFAULT_JSON_URL = "https://www.gstatic.com/ipranges/goog.json"
CLOUD_DEFAULT_JSON_URL = "https://www.gstatic.com/ipranges/cloud.json"

class GetElements(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.goog_json_url = 'goog_json_url' in metadata and metadata['goog_json_url'] or GOOG_DEFAULT_JSON_URL
        self.cloud_json_url = 'cloud_json_url' in metadata and metadata['cloud_json_url'] or CLOUD_DEFAULT_JSON_URL

    def get_elements(self):
        google_ips = self.get_google_cloud_ips()
        return google_ips

    def read_url(self, url):
        try:
            self.logger.debug('Loading JSON from URL: %s' % url)
            s = urllib.request.urlopen(url).read()
            return json.loads(s)
        except urllib.error.HTTPError as http_err:
            self.logger.warning("Invalid HTTP response from %s: %s" % (url, http_err))
            return {}
        except json.decoder.JSONDecodeError as json_err:
            self.logger.warning("Could not parse HTTP response from %s" % (url, json_err))
            return {}
        except urllib.error.URLError as err:
            self.logger.error("Error opening URL %s: %s" % (url, err))
            return {}

    def get_google_cloud_ips(self):
        goog_json = self.read_url(self.goog_json_url)
        cloud_json = self.read_url(self.cloud_json_url)
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
            ip_ranges = list(goog_cidrs.difference(cloud_cidrs))
            self.logger.debug("IP ranges for Google APIs and services default domains: %s" % json.dumps(ip_ranges))
            return ip_ranges
        else:
            self.logger.error("JSON data not properly loaded")
            return False

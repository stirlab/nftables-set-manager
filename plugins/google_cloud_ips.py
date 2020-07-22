import json
import urllib.request

GOOG_JSON_URL = "www.gstatic.com/ipranges/goog.json"
CLOUD_JSON_URL = "www.gstatic.com/ipranges/cloud.json"

class GetElements(object):

    def __init__(self, logger, metadata):
        self.logger = logger
        self.metadata = metadata

    def get_elements(self):
        google_ips = self.get_google_cloud_ips()
        return google_ips

    def read_url(self, url, fallback_to_http=False, attempts=2):
        if fallback_to_http:
            full_url = "http://" + url
        else:
            full_url = "https://" + url
        try:
            self.logger.debug('Loading JSON from URL: %s' % full_url)
            s = urllib.request.urlopen(full_url).read()
            return json.loads(s)
        except urllib.error.HTTPError as http_err:
            self.logger.warning("Invalid HTTP response from %s: %s" % (full_url, http_err))
            return {}
        except json.decoder.JSONDecodeError as json_err:
            self.logger.warning("Could not parse HTTP response from %s" % (full_url, json_err))
            return {}
        except urllib.error.URLError as err:
            if attempts > 1:
                attempts -=1
                self.logger.warning("Error opening URL; trying HTTP instead of HTTPS.")
                return read_url(url, fallback_to_http=True, attempts=attempts)
            else:
                self.logger.error("Error opening URL %s: %s" % (full_url, err))
                return {}

    def get_google_cloud_ips(self):
        goog_json = self.read_url(GOOG_JSON_URL)
        cloud_json = self.read_url(CLOUD_JSON_URL)
        if goog_json and cloud_json:
            self.logger.debug('%s published: %s' % (GOOG_JSON_URL, goog_json.get('creationTime')))
            self.logger.debug('%s published: %s' % (CLOUD_JSON_URL, cloud_json.get('creationTime')))
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

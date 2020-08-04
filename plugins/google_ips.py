import sys
sys.path.append('..')
from plugins import Plugin
import json
from file_retriever import FileRetriever

GOOG_DEFAULT_JSON_URL = "https://www.gstatic.com/ipranges/goog.json"
CLOUD_DEFAULT_JSON_URL = "https://www.gstatic.com/ipranges/cloud.json"

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.cloud_default_domains_only = 'cloud_default_domains_only' in metadata and metadata['cloud_default_domains_only'] or False
        self.goog_url = 'goog_url' in metadata and metadata['goog_url'] or GOOG_DEFAULT_JSON_URL
        self.cloud_url = 'cloud_url' in metadata and metadata['cloud_url'] or CLOUD_DEFAULT_JSON_URL
        self.goog_cache_file = 'goog_cache_file' in metadata and metadata['goog_cache_file'] or None
        self.cloud_cache_file = 'cloud_cache_file' in metadata and metadata['cloud_cache_file'] or None
        self.goog_file_retriever = FileRetriever(self.logger, self.goog_url, self.goog_cache_file)
        self.cloud_file_retriever = FileRetriever(self.logger, self.cloud_url, self.cloud_cache_file)

    def get_elements(self):
        google_ips = self.get_google_ips()
        return google_ips

    def get_google_ips(self):
        goog_json = self.goog_file_retriever.get_json()
        cloud_json = self.cloud_file_retriever.get_json()
        if goog_json and cloud_json:
            self.logger.debug('%s published: %s' % (self.goog_url, goog_json.get('creationTime')))
            self.logger.debug('%s published: %s' % (self.cloud_url, cloud_json.get('creationTime')))
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
                ip_ranges = list(goog_cidrs)
            self.logger.debug("IP ranges for Google APIs and services default domains: %s" % json.dumps(ip_ranges))
            return ip_ranges
        else:
            self.logger.error("JSON data not properly loaded")
            return False

import sys
sys.path.append('..')
from plugins import Plugin
import json
from file_retriever import FileRetriever

CLOUDFRONT_IP_RANGES_DEFAULT_JSON_URL = 'https://d7uri8nf7uskq.cloudfront.net/tools/list-cloudfront-ips'
IP_LISTS_DEFAULT = [
    'CLOUDFRONT_GLOBAL_IP_LIST',
]

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.url = 'url' in metadata and metadata['url'] or CLOUDFRONT_IP_RANGES_DEFAULT_JSON_URL
        self.ip_lists = 'ip_lists' in metadata and metadata['ip_lists'] or IP_LISTS_DEFAULT
        self.cache_file = 'cache_file' in metadata and metadata['cache_file'] or None
        self.file_retriever = FileRetriever(self.logger, self.url, self.cache_file)

    def get_elements(self):
        cloudfront_ips = self.get_cloudfront_ips()
        return cloudfront_ips

    def get_cloudfront_ips(self):
        data = self.file_retriever.get_json()
        if data:
            return self.build_elements(data)
        return False

    def build_elements(self, data):
        elements = []
        for ip_list in self.ip_lists:
            if ip_list in data:
                self.logger.debug("Adding elements from list %s: %s" % (ip_list, json.dumps(data[ip_list])))
                elements.extend(data[ip_list])
            else:
                self.logger.warn("List %s does not exist, skipping" % ip_list)
        return elements

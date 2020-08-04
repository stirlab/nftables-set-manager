import sys
sys.path.append('..')
from plugins import Plugin
import json
from file_retriever import FileRetriever

S3_IP_RANGES_DEFAULT_JSON_URL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'
REGIONS_DEFAULT = [
    'us-east-1',
]

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.url = 'url' in metadata and metadata['url'] or S3_IP_RANGES_DEFAULT_JSON_URL
        self.regions = 'regions' in metadata and metadata['regions'] or REGIONS_DEFAULT
        self.cache_file = 'cache_file' in metadata and metadata['cache_file'] or None
        self.file_retriever = FileRetriever(self.logger, self.url, self.cache_file)

    def get_elements(self):
        s3_ips = self.get_s3_ips_for_regions()
        return s3_ips

    def get_s3_ips_for_regions(self):
        data = self.file_retriever.get_json()
        if data:
            return self.build_elements(data)
        return False

    def build_elements(self, data):
        self.logger.debug("Adding elements from regions: %s" % json.dumps(self.regions))
        return [obj['ip_prefix'] for obj in data['prefixes'] if not self.regions or obj['region'] in self.regions]

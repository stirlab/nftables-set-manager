import sys
sys.path.append('..')
from plugins import Plugin
from file_retriever import FileRetriever

CLOUDFLARE_IP_RANGES_DEFAULT_JSON_URL = 'https://www.cloudflare.com/ips-v4'

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.url = 'url' in metadata and metadata['url'] or CLOUDFLARE_IP_RANGES_DEFAULT_JSON_URL
        self.cache_file = 'cache_file' in metadata and metadata['cache_file'] or None
        self.file_retriever = FileRetriever(self.logger, self.url, self.cache_file)

    def get_elements(self):
        cloudflare_ips = self.get_cloudflare_ips_for_types()
        return cloudflare_ips

    def get_cloudflare_ips_for_types(self):
        data = self.file_retriever.get()
        if data:
            elements = data.split()
            return elements
        return False

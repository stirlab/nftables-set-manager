import sys
sys.path.append('..')
from plugins import Plugin
from file_retriever import FileRetriever

GITHUB_IP_RANGES_DEFAULT_JSON_URL = 'https://api.github.com/meta'
IP_TYPES_DEFAULT = [
    'web',
    'api',
    'git',
]

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.url = 'url' in metadata and metadata['url'] or GITHUB_IP_RANGES_DEFAULT_JSON_URL
        self.ip_types = 'ip_types' in metadata and metadata['ip_types'] or IP_TYPES_DEFAULT
        self.cache_file = 'cache_file' in metadata and metadata['cache_file'] or None
        self.file_retriever = FileRetriever(self.logger, self.url, self.cache_file)

    def get_elements(self):
        github_ips = self.get_github_ips_for_types()
        return github_ips

    def get_github_ips_for_types(self):
        data = self.file_retriever.get_json()
        if data:
            return self.build_elements(data)
        return False

    def build_elements(self, data):
        elements = []
        for ip_type in data:
            if ip_type in self.ip_types:
                self.logger.debug("Adding elements for IP type: %s" % ip_type)
                for element in data[ip_type]:
                    if self.is_ipv4_address(element):
                        elements.append(element)
                    else
                        self.logger.debug("Skipping non-IPv4 address: %s" % element)
            else:
                self.logger.debug("Skipping IP type: %s" % ip_type)
        return elements

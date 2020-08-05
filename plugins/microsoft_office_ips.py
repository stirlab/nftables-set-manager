import sys
sys.path.append('..')
from plugins import Plugin
import uuid
import re

from file_retriever import FileRetriever

MICROSOFT_IP_RANGES_DEFAULT_JSON_URL = 'https://endpoints.office.com/endpoints/worldwide'
IPV4_CIDR_REGEX = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2}|)")

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.client_guid = 'client_guid' in metadata and metadata['client_guid'] or self.generate_client_guid()
        self.url = 'url' in metadata and metadata['url'] or '%s?clientrequestid=%s' % (MICROSOFT_IP_RANGES_DEFAULT_JSON_URL, self.client_guid)
        self.hostname_filters = 'hostname_filters' in metadata and set(metadata['hostname_filters']) or None
        self.cache_file = 'cache_file' in metadata and metadata['cache_file'] or None
        self.file_retriever = FileRetriever(self.logger, self.url, self.cache_file)

    def get_elements(self):
        microsoft_ips = self.get_microsoft_ips_for_hostnames()
        return microsoft_ips

    def generate_client_guid(self):
        return uuid.uuid4()

    def get_microsoft_ips_for_hostnames(self):
        data = self.file_retriever.get_json()
        if data:
            return self.build_elements(data)
        return False

    def extract_matching_hostnames(self, group):
        if self.hostname_filters is None:
            return True
        # TODO: Anything with no urls key is skipped for now, maybe also
        # provide support for serviceArea?
        if not 'urls' in group:
            return False
        common_hostnames = self.hostname_filters.intersection(set(group['urls']))
        for h in common_hostnames:
            self.hostname_filters.remove(h)
        self.logger.debug("Common hostnames in %s: %s" % (group['id'], common_hostnames))
        return len(common_hostnames) > 0

    def no_more_hostname_filters(self):
        return self.hostname_filters is not None and len(self.hostname_filters) == 0

    def build_elements(self, data):
        elements = []
        for group in data:
            has_matches = self.extract_matching_hostnames(group)
            if has_matches:
                self.logger.debug("Adding elements for id: %d" % group['id'])
                for element in group['ips']:
                    # TODO: Add IPv6 option.
                    if re.match(IPV4_CIDR_REGEX, element):
                        elements.append(element)
                if self.no_more_hostname_filters():
                    self.logger.debug("No more hostname filters, returning elements")
                    return elements
            else:
                self.logger.debug("Skipping elements for id: %d" % group['id'])
        return elements

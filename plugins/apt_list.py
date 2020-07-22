import socket
import json
from aptsources.sourceslist import SourcesList
from urllib.parse import urlparse

class GetElements(object):

    def __init__(self, logger, metadata):
        self.logger = logger
        self.metadata = metadata

    def get_elements(self):
        elements = []
        for hostname in self.get_unique_domains_from_apt_list():
            self.logger.debug("Looking up IP for hostname: %s" % hostname)
            try:
                ip = self.get_hostname_ip(hostname)
            except socket.gaierror:
                if 'ignore_missing_hosts' in metadata and metadata['ignore_missing_hosts']:
                    pass
                else:
                    raise RuntimeError("Invalid hostname: %s" % hostname)
            elements.append(ip)
        return elements

    def get_unique_domains_from_apt_list(self):
        sl = SourcesList()
        sl.refresh()
        domains = [urlparse(e.uri).netloc for e in sl if e.uri.startswith('http')]
        unique_domains = list(dict.fromkeys(domains))
        self.logger.debug("Parsed unique domains from apt lists: %s" % json.dumps(unique_domains))
        return unique_domains

    def get_hostname_ip(self, hostname):
        return socket.gethostbyname(hostname)

import json
from aptsources.sourceslist import SourcesList
from urllib.parse import urlparse
from berserker_resolver import Resolver
from plugins.resolv import GetElements as ResolvGetElements

class GetElements(object):

    def __init__(self, logger, metadata):
        self.logger = logger
        self.metadata = metadata
        self.ignore_missing_hosts = 'ignore_missing_hosts' in metadata and metadata['ignore_missing_hosts']
        self.ignore_hosts = 'ignore_hosts' in metadata and metadata['ignore_hosts'] or []
        self.nameservers = ResolvGetElements(logger, metadata).get_unix_dns_ips()
        self.resolver = Resolver(nameservers=self.nameservers)

    def get_elements(self):
        elements = []
        for hostname in self.get_unique_hosts_from_apt_list():
            if hostname in self.ignore_hosts:
                self.logger.debug("Ignoring hostname: %s" % hostname)
            else:
                self.logger.debug("Looking up IP for hostname: %s" % hostname)
                try:
                    ips = self.get_hostname_ips(hostname)
                except Exception as err:
                    if self.ignore_missing_hosts:
                        pass
                    else:
                        raise RuntimeError("Could not retrieve IPs for hostname %s: %s" % (hostname, err))
                elements.extend(ips)
        return elements

    def get_unique_hosts_from_apt_list(self):
        sl = SourcesList()
        sl.refresh()
        hosts = [urlparse(e.uri).netloc for e in sl if e.uri.startswith('http')]
        unique_hosts = list(dict.fromkeys(hosts))
        self.logger.debug("Parsed unique hosts from apt lists: %s" % json.dumps(unique_hosts))
        return unique_hosts

    def get_hostname_ips(self, hostname):
        result = self.resolver.query(hostname)
        return [elem.to_text() for elem in result]

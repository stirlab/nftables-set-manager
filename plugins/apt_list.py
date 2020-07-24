import json
from aptsources.sourceslist import SourcesList
from urllib.parse import urlparse
from berserker_resolver import Resolver
from plugins.resolv import GetElements as ResolvGetElements

class GetElements(object):

    def __init__(self, metadata, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args
        self.ignore_missing_hosts = 'ignore_missing_hosts' in metadata and metadata['ignore_missing_hosts']
        self.ignore_hosts = 'ignore_hosts' in metadata and metadata['ignore_hosts'] or []
        self.additional_hosts = 'additional_hosts' in metadata and metadata['additional_hosts'] or []
        self.nameservers = ResolvGetElements(self.metadata,self.logger, self.config, self.args).get_unix_dns_ips()
        self.nameservers.extend('dns_nameservers' in config and config['dns_nameservers'] or [])
        self.resolver = Resolver(nameservers=self.nameservers)

    def get_elements(self):
        elements = []
        apt_hosts = self.get_unique_hosts_from_apt_list()
        apt_hosts.extend(self.additional_hosts)
        for hostname in set(apt_hosts):
            if hostname in self.ignore_hosts:
                self.logger.debug("Ignoring hostname: %s" % hostname)
            else:
                self.logger.debug("Looking up IP for hostname: %s" % hostname)
                try:
                    ips = self.get_hostname_ips(hostname)
                    elements.extend(ips)
                except Exception as err:
                    if self.ignore_missing_hosts:
                        pass
                    else:
                        raise RuntimeError("Could not retrieve IPs for hostname %s: %s" % (hostname, err))
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

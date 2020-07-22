from berserker_resolver import Resolver
from plugins.resolv import GetElements as ResolvGetElements

class GetElements(object):

    def __init__(self, logger, metadata):
        self.logger = logger
        self.metadata = metadata
        self.ignore_missing_hosts = 'ignore_missing_hosts' in metadata and metadata['ignore_missing_hosts']
        self.nameservers = ResolvGetElements(logger, metadata).get_unix_dns_ips()
        self.resolver = Resolver(nameservers=self.nameservers)

    def get_elements(self):
        elements = []
        for hostname in self.metadata['hostnames']:
            self.logger.debug("Looking up IPs for hostname: %s" % hostname)
            try:
                ips = self.get_hostname_ips(hostname)
            except Exception as err:
                if self.ignore_missing_hosts:
                    pass
                else:
                    raise RuntimeError("Could not retrieve IPs for hostname %s: %s" % (hostname, err))
            elements.extend(ips)
        return elements

    def get_hostname_ips(self, hostname):
        result = self.resolver.query(hostname)
        return [elem.to_text() for elem in result]

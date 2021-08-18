import sys
sys.path.append('..')
from plugins import Plugin

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.ignore_missing_hosts = 'ignore_missing_hosts' in metadata and metadata['ignore_missing_hosts']

    def get_elements(self):
        elements = []
        for hostname in self.metadata['hostnames']:
            ips = []
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
        if self.is_ipv4_address(hostname):
            return [hostname]
        result = self.resolver.query(hostname)
        return [elem.to_text() for elem in result]

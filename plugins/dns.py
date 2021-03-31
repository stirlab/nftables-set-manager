import sys
import re
sys.path.append('..')
from plugins import Plugin

IPV4_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"

class GetElements(Plugin):

    def __init__(self, metadata, resolver, logger, config, args):
        super().__init__(metadata, resolver, logger, config, args)
        self.ignore_missing_hosts = 'ignore_missing_hosts' in metadata and metadata['ignore_missing_hosts']

    def is_ip_address(self, hostname):
        return bool(re.match(IPV4_REGEX, hostname))

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
        if self.is_ip_address(hostname):
            return [hostname]
        result = self.resolver.query(hostname)
        return [elem.to_text() for elem in result]

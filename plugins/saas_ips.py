import sys
sys.path.append('..')
from plugins import Plugin

SAAS_HOSTNAMES = [
    "drbd.io",
]

class GetElements(Plugin):

    def get_elements(self):
        elements = []
        for hostname in SAAS_HOSTNAMES:
            self.logger.debug("Looking up IPs for hostname: %s" % hostname)
            try:
                ips = self.get_hostname_ips(hostname)
                elements.extend(ips)
            except Exception as err:
                self.logger.error("Could not retrieve IPs for hostname %s: %s" % (hostname, err))
        return elements

    def get_hostname_ips(self, hostname):
        result = self.resolver.query(hostname)
        return [elem.to_text() for elem in result]

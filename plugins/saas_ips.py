SAAS_HOSTNAMES = [
    "drbd.io",
]

class GetElements(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.resolver = resolver
        self.logger = logger
        self.config = config
        self.args = args

    def get_elements(self):
        elements = []
        for hostname in SAAS_HOSTNAMES:
            self.logger.debug("Looking up IPs for hostname: %s" % hostname)
            try:
                ips = self.get_hostname_ips(hostname)
            except Exception as err:
                raise RuntimeError("Could not retrieve IPs for hostname %s: %s" % (hostname, err))
            elements.extend(ips)
        return elements

    def get_hostname_ips(self, hostname):
        result = self.resolver.query(hostname)
        return [elem.to_text() for elem in result]

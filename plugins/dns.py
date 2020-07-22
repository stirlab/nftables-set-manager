import socket

class GetElements(object):

    def __init__(self, logger, metadata):
        self.logger = logger
        self.metadata = metadata

    def get_elements(self):
        elements = []
        for hostname in self.metadata['hostnames']:
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

    def get_hostname_ip(self, hostname):
        return socket.gethostbyname(hostname)

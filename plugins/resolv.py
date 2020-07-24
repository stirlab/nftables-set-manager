import socket

class GetElements(object):

    def __init__(self, metadata, logger, config, args):
        self.metadata = metadata
        self.logger = logger
        self.config = config
        self.args = args

    def get_elements(self):
        return self.get_unix_dns_ips()

    def get_unix_dns_ips(self):
        dns_ips = []
        with open('/etc/resolv.conf') as fp:
            for cnt, line in enumerate(fp):
                columns = line.split()
                if len(columns) > 0 and columns[0] == 'nameserver':
                    ip = columns[1:][0]
                    if self.is_valid_ipv4_address(ip):
                        self.logger.debug('Found DNS IP: %s' % ip)
                        dns_ips.append(ip)
        return dns_ips

    def is_valid_ipv4_address(self, address):
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3

import socket

RESOLV_DEFAULT = "/etc/resolv.conf"

class Resolv(object):

    def __init__(self, logger, config, args):
        self.logger = logger
        self.config = config
        self.args = args
        self.resolv_file = 'resolv_file' in self.config and self.config['resolv_file'] or RESOLV_DEFAULT

    def get_elements(self):
        return self.get_unix_dns_ips()

    def get_unix_dns_ips(self):
        self.logger.debug('Parsing %s for nameservers' % self.resolv_file)
        dns_ips = []
        with open(self.resolv_file) as fp:
            for cnt, line in enumerate(fp):
                columns = line.split()
                if len(columns) > 0 and columns[0] == 'nameserver':
                    ip = columns[1:][0]
                    if self.is_valid_ipv4_address(ip) and ip not in dns_ips:
                        self.logger.debug('Found DNS IP: %s' % ip)
                        dns_ips.append(ip)
        return dns_ips

    def is_valid_ipv4_address(self, address):
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3

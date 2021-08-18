import re

IPV4_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"

class Plugin(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.resolver = resolver
        self.logger = logger
        self.config = config
        self.args = args

    def is_ipv4_address(self, hostname):
        return bool(re.match(IPV4_REGEX, hostname))

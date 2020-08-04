class Plugin(object):

    def __init__(self, metadata, resolver, logger, config, args):
        self.metadata = metadata
        self.resolver = resolver
        self.logger = logger
        self.config = config
        self.args = args

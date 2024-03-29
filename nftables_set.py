import subprocess
import logging
import json

logging.basicConfig(level=logging.INFO)

DEFAULT_NFT_BINARY = '/usr/sbin/nft'

class NftablesSet(object):

    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.nft_binary = 'nft_binary' in config and config['nft_binary'] or DEFAULT_NFT_BINARY
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)

    def set_operation(self, op, set_family, set_table, set_name, elements=None):
        if op == 'flush':
            command = [
                op,
                'set',
                set_family,
                set_table,
                set_name,
            ]
        else:
            if isinstance(elements, str):
                elements = [elements]
            command = [
                op,
                'element',
                set_family,
                set_table,
                set_name,
                '{ %s }' % ', '.join(elements),
            ]
        self.logger.debug("Operation: %s, on set '%s %s %s', elements: %s" % (op, set_family, set_table, set_name, json.dumps(elements)))
        self.run(command, capture_output=False)

    def get_set_elements(self, set_family, set_table, set_name):
        data = self.run([
            'list',
            'set',
            set_family,
            set_table,
            set_name,
        ])
        try:
            set_data = data[0]['set']
        except KeyError:
            set_data = data[1]['set']
        elements = 'elem' in set_data and set_data['elem'] or []
        self.logger.debug("Elements for set '%s %s %s': %s" % (set_family, set_table, set_name, json.dumps(elements)))
        return elements

    def run(self, command_args, capture_output=True):
        command = [
            self.nft_binary,
            '-j',
        ]
        command.extend(command_args)
        kwargs = {}
        if capture_output:
            kwargs.update({
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'universal_newlines': True,
            })
        self.logger.debug("Running command: %s" % ' '.join(command))
        try:
            proc = subprocess.Popen(command, **kwargs)
            stdout, stderr = proc.communicate()
            returncode = proc.returncode
        except Exception as e:
            stdout = ''
            stderr = e.message if hasattr(e, 'message') else str(e)
            returncode = 1
        if returncode != 0:
            raise RuntimeError("Failed command '%s': %s" % (' '.join(command), stderr))
        if capture_output:
            data = json.loads(stdout)
            return data['nftables']

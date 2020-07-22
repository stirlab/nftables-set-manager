import subprocess
import logging
import json

logging.basicConfig(level=logging.WARNING)

class NftablesSet(object):

    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)

    def set_operation(self, op, set_type, set_table, set_name, value):
        self.run([
            op,
            'element',
            set_type,
            set_table,
            set_filter,
            '{ %s }' % value,
        ])

    def get_set_elements(self, set_type, set_table, set_name):
        data = self.run([
            'list',
            'set',
            set_type,
            set_table,
            set_filter,
        ])
        set_data = data[0]['set']
        return 'elem' in set_data and set_data['elem'] or []

    def run(self, command_args, capture_output=True):
        command = [
            'nft',
            '-j',
        ]
        command.append(command_args)
        kwargs = {}
        if capture_output:
            kwargs.update({
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'universal_newlines': True,
            })
        try:
            proc = subprocess.Popen(command, **kwargs)
            stdout, stderr = proc.communicate()
            returncode = proc.returncode
        except Exception as e:
            stdout = ''
            stderr = e.message if hasattr(e, 'message') else str(e)
            returncode = 1
        if returncode != 0:
            raise RuntimeError("Failed command '%s': %s", % (' '.join(command), stderr))
        if capture_output:
            data = json.loads(stdout)
            return data['nftables']

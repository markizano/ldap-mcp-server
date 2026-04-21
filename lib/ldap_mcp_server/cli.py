'''
Command line interface entrypoint for `ldap-mcp-server` command.

This module will be responsible for parsing command line arguments.
'''

import os, sys
from signal import signal, SIGINT
from argparse import ArgumentParser, RawTextHelpFormatter
from kizano import getLogger
log = getLogger(__name__)

import ldap_mcp_server

def interrupt(signal, frame):
    log.error('Caught ^C interrupt, exiting...')
    sys.exit(signal)

class Cli(object):
    '''
    Usage: %(prog)s [options] [command]
    '''

    def __init__(self, config: dict):
        self.config = config
        self.getOptions()
        log.debug(f'Final config: {self.config}')

    def getOptions(self) -> None:
        '''
        Gets command line arguments.
        '''
        options = ArgumentParser(
            usage=self.__doc__,
            formatter_class=RawTextHelpFormatter
        )

        options.add_argument(
            '--log-level', '-l',
            action='store',
            dest='log_level',
            help='How verbose should this application be?',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            type=str.upper
        )

        options.add_argument(
            '--version',
            action='store_true',
            dest='print_version',
            help='Print version and exit.',
        )

        mcp_port = os.environ.get('MCP_PORT', '8080')
        default_addr = mcp_port if mcp_port.startswith(':') else f':{mcp_port}'
        options.add_argument(
            '--addr', '-addr',
            action='store',
            dest='addr',
            default=default_addr,
            help='MCP listen address (default :8080, overridable via MCP_PORT).',
        )

        options.add_argument(
            '--url',
            action='store',
            dest='url',
            help='LDAP server URL such as ldap://host:389 or ldaps://host:636.',
        )

        options.add_argument(
            '--bind-dn',
            action='store',
            dest='bind_dn',
            help='Distinguished name used for LDAP bind.',
        )

        options.add_argument(
            '--bind-password',
            action='store',
            dest='bind_password',
            default=os.environ.get('LDAP_BIND_PASSWORD'),
            help='Password used for LDAP bind (or LDAP_BIND_PASSWORD env var).',
        )

        options.add_argument(
            '--starttls',
            action='store_true',
            dest='starttls',
            help='Upgrade ldap:// connection to TLS via StartTLS.',
        )

        options.add_argument(
            '--insecure',
            action='store_true',
            dest='insecure',
            help='Skip TLS certificate verification (testing only).',
        )

        options.add_argument(
            '--read-write',
            action='store_true',
            dest='read_write',
            help='Enable add/modify/delete tools (default is read-only mode).',
        )

        options.add_argument(
            '--timeout',
            action='store',
            dest='timeout',
            type=int,
            default=30,
            help='Per-request LDAP timeout in seconds (default: 30).',
        )

        opts = options.parse_args()

        if opts.print_version:
            import ldap_mcp_server._version
            print(f'mkzforge: {ldap_mcp_server._version.__version__}')
            sys.exit(0)

        if not 'LOG_LEVEL' in os.environ:
            os.environ['LOG_LEVEL'] = opts.log_level
            log.setLevel(opts.log_level)

        # Filter out None values so config file defaults are not overridden.
        opts_dict = {k: v for k, v in vars(opts).items() if v is not None}
        self.config.update(opts_dict)

    def execute(self):
        '''
        Interprets command line options and calls the subsequent actions to take.
        These will be built out as sub-modules to this module.
        '''
        log.info('Welcome to LDAP MCP Server!')
        signal(SIGINT, interrupt)
        return ldap_mcp_server.server.serve(self.config)

__all__ = ['Cli']

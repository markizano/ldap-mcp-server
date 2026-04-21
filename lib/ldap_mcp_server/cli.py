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

        options.add_argument(
            '--host',
            action='store',
            dest='host',
            default=os.getenv('MCP_HOST', '0.0.0.0'),
            help='MCP listen/bind address (defaults to $MCP_HOST, 0.0.0.0 if unset).',
        )
        options.add_argument(
            '--port',
            action='store',
            dest='port',
            default=os.getenv('MCP_PORT', '9090'),
            help='MCP listen/bind address (defaults to $MCP_PORT, 9090 if unset).',
        )

        options.add_argument(
            '--url',
            action='store',
            dest='url',
            default=os.getenv('LDAP_URI', 'ldap://localhost:389'),
            help='LDAP server URL such as ldap://localhost:389 or ldaps://ldap.example.com:636. Defaults to localhost. If unset, uses $LDAP_URI',
        )

        options.add_argument(
            '--bind-dn',
            action='store',
            dest='bind_dn',
            default=os.environ.get('LDAP_BIND_DN'),
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
            print(f'ldap-mcp-server: {ldap_mcp_server._version.__version__}')
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

"""Command-line interface for LDAP MCP Server.

This module parses CLI flags and merges them with environment-based configuration.
CLI flags take precedence over environment variables.
"""

import argparse
import sys
from ldap_mcp_server.config import Config


def parse_args(argv: list[str] | None = None) -> Config:
    """Parse command-line arguments and build Config.

    CLI flags take precedence over environment variables.
    Environment variables are loaded via Config.from_env() as defaults.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Config object with merged settings
    """
    # Load defaults from environment
    env_cfg = Config.from_env()

    parser = argparse.ArgumentParser(
        prog='ldap-mcp-server',
        description='MCP server for LDAP directory operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (overridden by CLI flags):
  LDAP_URI                  LDAP server URL (default: ldap://localhost:389)
  LDAP_BIND_DN              Bind DN for service account
  LDAP_BIND_PASSWORD        Bind password
  MCP_HOST                  Host to bind to (default: 0.0.0.0)
  MCP_PORT                  Port to listen on (default: 9090)
  LOG_LEVEL                 Logging level (default: INFO)
  LDAP_MCP_SERVER_API_KEY   API key for client authentication (SSE mode only)

Examples:
  # stdio transport (no auth needed)
  ldap-mcp-server --transport stdio --read-write

  # SSE transport with API key
  export LDAP_MCP_SERVER_API_KEY=secret123
  ldap-mcp-server --transport sse --host 0.0.0.0 --port 9090
        """
    )

    # Transport
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse'],
        default=env_cfg.transport,
        help='Transport mode (default: sse)'
    )

    # Server binding (SSE mode)
    parser.add_argument(
        '--host',
        default=env_cfg.host,
        help=f'Host to bind to (default: {env_cfg.host})'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=env_cfg.port,
        help=f'Port to listen on (default: {env_cfg.port})'
    )

    # LDAP connection
    parser.add_argument(
        '--url',
        default=env_cfg.url,
        help=f'LDAP server URL (default: {env_cfg.url})'
    )
    parser.add_argument(
        '--bind-dn',
        default=env_cfg.bind_dn,
        help='Bind DN for service account'
    )
    parser.add_argument(
        '--bind-password',
        default=env_cfg.bind_password,
        help='Bind password'
    )

    # TLS options
    parser.add_argument(
        '--starttls',
        action='store_true',
        default=env_cfg.use_starttls,
        help='Use StartTLS (cannot be used with ldaps://)'
    )
    parser.add_argument(
        '--insecure',
        action='store_true',
        default=env_cfg.insecure_tls,
        help='Skip TLS certificate verification (INSECURE)'
    )

    # Operation mode
    parser.add_argument(
        '--read-write',
        action='store_true',
        default=env_cfg.read_write,
        help='Enable write operations (add, modify, delete)'
    )

    # Timeouts
    parser.add_argument(
        '--timeout',
        type=int,
        default=env_cfg.timeout,
        help=f'LDAP operation timeout in seconds (default: {env_cfg.timeout})'
    )

    # Logging
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=env_cfg.log_level,
        help=f'Logging level (default: {env_cfg.log_level})'
    )

    args = parser.parse_args(argv)

    # Build Config from parsed args (env vars already loaded as defaults)
    cfg = Config(
        transport=args.transport,
        host=args.host,
        port=args.port,
        url=args.url,
        bind_dn=args.bind_dn,
        bind_password=args.bind_password,
        use_starttls=args.starttls,
        insecure_tls=args.insecure,
        read_write=args.read_write,
        timeout=args.timeout,
        log_level=args.log_level.upper(),
        api_key=env_cfg.api_key,  # API key only from env, not CLI
    )

    # Validate configuration
    try:
        cfg.validate()
    except ValueError as e:
        parser.error(str(e))

    return cfg


__all__ = ['parse_args']

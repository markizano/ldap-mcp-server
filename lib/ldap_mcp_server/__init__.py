"""LDAP MCP Server - MCP endpoint for LDAP directory operations.

This module provides the main entry point for the LDAP MCP server.
Environment variables are loaded from .env file on import.
"""

import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main() -> int:
    """Main entry point for ldap-mcp-server command.

    Parses CLI arguments, sets up logging, and starts the server.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    from ldap_mcp_server.cli import parse_args
    from ldap_mcp_server.server import serve

    # Parse configuration
    config = parse_args()

    # Set up logging
    logging.basicConfig(
        level=config.log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr,
    )

    # Start server
    return serve(config)


__all__ = ['main']

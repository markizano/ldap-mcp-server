import os
from dotenv import load_dotenv

import kizano
import ldap_mcp_server.server as server
import ldap_mcp_server.cli as cli

# Load environment variables from .env file
load_dotenv()

def main() -> int:
    '''
    Main entry point for this application.
    Let's you run the MCP server for LDAP.
    '''
    kizano.log.setLevel(99)
    config = kizano.getConfig()
    myMCPServer = cli.Cli(config)
    myMCPServer.execute()
    return 0

__all__ = ["server", "cli"]

"""MCP resource registrations for LDAP directory information.

This module registers MCP resources that expose LDAP server metadata
and individual entry retrieval via URI patterns.
"""

import json
import logging
from urllib.parse import unquote
from mcp.server.fastmcp import FastMCP
from ldap_mcp_server.ldap_client import LDAPClient, LDAPNotFoundError
from ldap_mcp_server.ldif import entry_to_ldif

log = logging.getLogger(__name__)


def register_resources(mcp: FastMCP, client: LDAPClient) -> None:
    """Register LDAP resources on the FastMCP instance.

    Must be called before mcp.sse_app() or mcp.run().

    Resources registered:
    - ldap://root-dse: Server root DSE metadata
    - ldap://entry/{dn}: Individual entry by URL-encoded DN

    Args:
        mcp: FastMCP server instance
        client: Connected LDAP client
    """

    @mcp.resource('ldap://root-dse')
    async def get_root_dse() -> str:
        """Root DSE attributes for the connected LDAP server.

        The Root DSE (RFC 4512) provides server metadata including:
        - Supported LDAP versions
        - Naming contexts
        - Supported controls and extensions

        Returns:
            JSON representation of Root DSE entry.
        """
        try:
            entry = client.read_root_dse(attributes=None)
            return json.dumps({'root_dse': entry}, indent=2)
        except Exception as e:
            log.error('get_root_dse failed: %s', e, exc_info=True)
            return json.dumps({'error': str(e)})

    @mcp.resource('ldap://entry/{dn}')
    async def get_ldap_entry(dn: str) -> str:
        """Retrieve an LDAP entry by DN (URL-encoded in the URI).

        The DN must be URL-encoded in the resource URI.
        Example URI: ldap://entry/uid%3Djsmith%2Cou%3Dusers%2Cdc%3Dexample%2Cdc%3Dcom

        Args:
            dn: URL-encoded distinguished name

        Returns:
            LDIF representation of the entry, or JSON error if not found.
        """
        try:
            decoded_dn = unquote(dn)
            entry = client.get_entry(decoded_dn, attributes=None)
            return entry_to_ldif(entry['dn'], entry.get('attributes', {}))
        except LDAPNotFoundError:
            return json.dumps({'error': f'not found: {dn}'})
        except Exception as e:
            log.error('get_ldap_entry failed: %s', e, exc_info=True)
            return json.dumps({'error': str(e)})


__all__ = ['register_resources']

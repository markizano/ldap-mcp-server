"""MCP tool registrations for LDAP operations.

This module registers all LDAP CRUD tools with the FastMCP server instance.
Tools are defined inside register_tools() to close over the client and read_write flag.
"""

import json
import logging
from typing import Any, List, Optional
from mcp.server.fastmcp import FastMCP
from ldap_mcp_server.ldap_client import LDAPClient, LDAPNotFoundError, SearchScope, DerefAliases
from ldap_mcp_server.ldif import entries_to_ldif, entry_to_ldif

log = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, client: LDAPClient, read_write: bool) -> None:
    """Register all LDAP tools on the FastMCP instance.

    Must be called before mcp.sse_app() or mcp.run().

    Args:
        mcp: FastMCP server instance
        client: Connected LDAP client
        read_write: If True, register write operations (add, modify, delete)
    """

    @mcp.tool()
    async def search_entries(
        base_dn: str,
        filter: str,
        scope: str = 'sub',
        attributes: Optional[List[str]] = None,
        size_limit: int = 0,
        types_only: bool = False,
        page_size: int = 0,
        deref_aliases: str = 'never',
        output_format: str = 'ldif',
    ) -> str:
        """Execute an LDAP search operation.

        Args:
            base_dn: Base distinguished name for the search.
            filter: LDAP search filter (RFC 4515), e.g. (objectClass=*).
            scope: Search scope — base, one, or sub (default: sub).
            attributes: Attribute names to return. Omit or pass empty list for all attributes.
            size_limit: Max entries to return. 0 means server default.
            types_only: Return attribute names without values.
            page_size: Simple Paged Results control size. 0 disables paging.
            deref_aliases: Alias dereferencing — never, searching, finding, or always.
            output_format: Output format — ldif (default) or json.

        Returns:
            LDIF or JSON representation of search results.
        """
        try:
            scope_enum = SearchScope(scope.lower())
            deref_enum = DerefAliases(deref_aliases.lower())
            entries = client.search(
                base_dn=base_dn,
                filter_string=filter,
                scope=scope_enum,
                attributes=attributes or None,
                size_limit=max(0, size_limit),
                types_only=types_only,
                deref_aliases=deref_enum,
                page_size=max(0, min(page_size, 2**32 - 1)),
            )
            if output_format == 'json':
                return json.dumps({'count': len(entries), 'entries': entries}, indent=2)
            return f'# {len(entries)} entries found\n\n{entries_to_ldif(entries)}'
        except LDAPNotFoundError:
            return 'error: base DN not found'
        except Exception as e:
            log.error('search_entries failed: %s', e, exc_info=True)
            return f'error: {e}'

    @mcp.tool()
    async def get_entry(
        dn: str,
        attributes: Optional[List[str]] = None,
        output_format: str = 'ldif',
    ) -> str:
        """Retrieve a single LDAP entry by distinguished name.

        Args:
            dn: The distinguished name of the entry.
            attributes: Attribute names to return. Omit for all.
            output_format: Output format — ldif (default) or json.

        Returns:
            LDIF or JSON representation of the entry.
        """
        try:
            entry = client.get_entry(dn, attributes or None)
            if output_format == 'json':
                return json.dumps({'entry': entry}, indent=2)
            return entry_to_ldif(entry['dn'], entry.get('attributes', {}))
        except LDAPNotFoundError:
            return f'error: entry not found — {dn}'
        except Exception as e:
            log.error('get_entry failed: %s', e, exc_info=True)
            return f'error: {e}'

    if not read_write:
        return  # stop here for read-only mode

    @mcp.tool()
    async def add_entry(dn: str, attributes: dict[str, List[str]]) -> str:
        """Create a new LDAP entry.

        Args:
            dn: Distinguished name for the new entry.
            attributes: Map of attribute names to lists of string values.
                        Example: {"objectClass": ["inetOrgPerson"], "cn": ["John Smith"]}

        Returns:
            Success message or error description.
        """
        try:
            client.add_entry(dn, attributes)
            return f'created: {dn}'
        except Exception as e:
            log.error('add_entry failed: %s', e, exc_info=True)
            return f'error: {e}'

    @mcp.tool()
    async def modify_entry(dn: str, changes: List[dict[str, Any]]) -> str:
        """Modify attributes of an existing LDAP entry.

        Args:
            dn: Distinguished name of the entry to modify.
            changes: List of modification objects, each with:
                     - operation: "add", "replace", or "delete"
                     - attribute: attribute name (string)
                     - values: list of string values (may be empty for delete)

        Returns:
            Success message or error description.
        """
        try:
            client.modify_entry(dn, changes)
            return f'modified: {dn}'
        except Exception as e:
            log.error('modify_entry failed: %s', e, exc_info=True)
            return f'error: {e}'

    @mcp.tool()
    async def delete_entry(dn: str) -> str:
        """Delete an LDAP entry by distinguished name.

        Args:
            dn: The distinguished name to delete.

        Returns:
            Success message or error description.
        """
        try:
            client.delete_entry(dn)
            return f'deleted: {dn}'
        except Exception as e:
            log.error('delete_entry failed: %s', e, exc_info=True)
            return f'error: {e}'


__all__ = ['register_tools']

"""
MCP server implementation for LDAP with HTTP/SSE transport.
"""

from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP
from kizano import getLogger

from ldap_mcp_server.ldap_client import LDAPClient, LDAPNotFoundError, SearchScope, DerefAliases

log = getLogger(__name__)

def serve(cfg: dict) -> int:
    """
    Main entry point to start the MCP server.

    Args:
        cfg: Configuration dictionary

    Returns:
        Exit code
    """
    ldap_client: LDAPClient = None

    # Extract configuration
    url = cfg.get('url')
    if not url:
        log.error("LDAP URL is required (--url)")
        return 1

    bind_dn = cfg.get('bind_dn', '')
    bind_password = cfg.get('bind_password', '')
    starttls = cfg.get('starttls', False)
    insecure = cfg.get('insecure', False)
    read_write = cfg.get('read_write', False)
    timeout = cfg.get('timeout', 30)
    host = cfg.get('host', '0.0.0.0')
    port = int(cfg.get('port', 8080))

    # Log startup info
    mode = "read-write" if read_write else "read-only"
    log.info(f"Starting LDAP MCP Server on {host}:{port} ({mode} mode)")
    log.info(f"LDAP URL: {url}")
    if bind_dn:
        log.info(f"Bind DN: {bind_dn}")
    else:
        log.info("Bind DN: (anonymous)")

    proto = "StartTLS" if starttls else url
    log.info(f"TLS mode: {proto} (insecure={insecure})")

    # Initialize LDAP client
    try:
        ldap_client = LDAPClient(
            url=url,
            bind_dn=bind_dn,
            bind_password=bind_password,
            use_starttls=starttls,
            insecure_tls=insecure,
            default_timeout=timeout,
        )
        log.info("Connected to LDAP server successfully")
    except Exception as e:
        log.error(f"Failed to connect to LDAP server: {e}")
        return 1

    # Create FastMCP server
    mcp = FastMCP(
        name="ldap-mcp",
        host=host,
        port=port,
        sse_path="/sse",
        message_path="/messages",
    )

    # Register search_entries tool
    @mcp.tool()
    async def search_entries(
        base_dn: str,
        filter: str,
        scope: str = "sub",
        attributes: List[str] = None,
        size_limit: int = 0,
        types_only: bool = False,
        page_size: int = 0,
        deref_aliases: str = "never"
    ) -> Dict[str, Any]:
        """
        Execute an LDAP search operation.

        Args:
            base_dn: Base distinguished name for the search
            filter: LDAP search filter (RFC 4515)
            scope: Search scope (base, one, or sub)
            attributes: Attributes to return (empty = all)
            size_limit: Maximum entries to return (0 = server default)
            types_only: Return only attribute types without values
            page_size: Paging size (0 = no paging)
            deref_aliases: Alias dereferencing (never, searching, finding, always)
        """
        try:
            scope_enum = SearchScope(scope.lower())
            deref_enum = DerefAliases(deref_aliases.lower())

            entries = ldap_client.search(
                base_dn=base_dn,
                filter_string=filter,
                scope=scope_enum,
                attributes=attributes,
                size_limit=size_limit,
                types_only=types_only,
                deref_aliases=deref_enum,
                page_size=min(page_size, 2**32 - 1) if page_size > 0 else 0,
            )

            return {
                "entries": entries,
                "count": len(entries),
            }
        except LDAPNotFoundError as e:
            return {"error": f"LDAP entry not found: {e}"}
        except Exception as e:
            log.error(f"search_entries error: {e}", exc_info=True)
            return {"error": str(e)}

    # Register get_entry tool
    @mcp.tool()
    async def get_entry(
        dn: str,
        attributes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve a single LDAP entry by DN.

        Args:
            dn: The distinguished name of the entry
            attributes: Attributes to return (empty = all)
        """
        try:
            entry = ldap_client.get_entry(dn, attributes)
            return {"entry": entry}
        except LDAPNotFoundError:
            return {"error": "LDAP entry not found"}
        except Exception as e:
            log.error(f"get_entry error: {e}", exc_info=True)
            return {"error": str(e)}

    # Register write tools if enabled
    if read_write:
        @mcp.tool()
        async def add_entry(
            dn: str,
            attributes: Dict[str, List[str]]
        ) -> Dict[str, Any]:
            """
            Create a new LDAP entry.

            Args:
                dn: Distinguished name for the new entry
                attributes: Map of attribute names to string arrays
            """
            try:
                ldap_client.add_entry(dn, attributes)
                return {"success": True, "message": f"Entry {dn} created successfully"}
            except Exception as e:
                log.error(f"add_entry error: {e}", exc_info=True)
                return {"error": str(e)}

        @mcp.tool()
        async def modify_entry(
            dn: str,
            changes: List[Dict[str, Any]]
        ) -> Dict[str, Any]:
            """
            Modify attributes of an LDAP entry.

            Args:
                dn: The distinguished name of the entry
                changes: List of modifications (operation, attribute, values)
            """
            try:
                ldap_client.modify_entry(dn, changes)
                return {"success": True, "message": f"Entry {dn} modified successfully"}
            except Exception as e:
                log.error(f"modify_entry error: {e}", exc_info=True)
                return {"error": str(e)}

        @mcp.tool()
        async def delete_entry(dn: str) -> Dict[str, Any]:
            """
            Delete an LDAP entry by DN.

            Args:
                dn: The distinguished name to delete
            """
            try:
                ldap_client.delete_entry(dn)
                return {"success": True, "message": f"Entry {dn} deleted successfully"}
            except Exception as e:
                log.error(f"delete_entry error: {e}", exc_info=True)
                return {"error": str(e)}

    # Register root-dse resource
    @mcp.resource("ldap://root-dse")
    async def get_root_dse() -> str:
        """Root DSE attributes for the LDAP server."""
        try:
            entry = ldap_client.read_root_dse(attributes=None)
            import json
            return json.dumps({"root_dse": entry}, indent=2)
        except Exception as e:
            log.error(f"get_root_dse error: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    # Register entry resource template
    @mcp.resource("ldap://entry/{dn}")
    async def get_ldap_entry(dn: str) -> str:
        """Retrieve an LDAP entry by DN (URL-escaped)."""
        try:
            from urllib.parse import unquote
            decoded_dn = unquote(dn)
            entry = ldap_client.get_entry(decoded_dn, attributes=None)
            import json
            return json.dumps({"entry": entry}, indent=2)
        except LDAPNotFoundError:
            import json
            return json.dumps({"error": f"LDAP entry not found: {dn}"})
        except Exception as e:
            log.error(f"get_ldap_entry error: {e}", exc_info=True)
            import json
            return json.dumps({"error": str(e)})

    # Log available tools
    available_tools = "search_entries, get_entry"
    if read_write:
        available_tools += ", add_entry, modify_entry, delete_entry"
    log.info(f"Available tools: {available_tools}")
    log.info("Available resources: ldap://root-dse, ldap://entry/{{dn}}")
    log.info(f"SSE endpoint: http://{host}:{port}/sse")
    log.info(f"Messages endpoint: http://{host}:{port}/messages")

    # Run server
    try:
        mcp.run(transport='sse')
        return 0
    except KeyboardInterrupt:
        log.info("Received shutdown signal")
        return 0
    except Exception as e:
        log.error(f"Server error: {e}", exc_info=True)
        return 1
    finally:
        if ldap_client:
            ldap_client.close()
        log.info("Server shutdown complete")


__all__ = ['serve']

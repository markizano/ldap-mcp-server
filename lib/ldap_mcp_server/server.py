"""
MCP server implementation for LDAP.

This module implements the main MCP server with SSE transport.
"""

from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
from kizano import getLogger

from ldap_mcp_server.ldap_client import LDAPClient
from ldap_mcp_server.tools import Toolset
from ldap_mcp_server.resources import ResourceSet

log = getLogger(__name__)


def create_mcp_server(client: LDAPClient, read_write: bool) -> tuple[Server, Toolset, ResourceSet]:
    """
    Create and configure MCP server.

    Args:
        client: LDAP client instance
        read_write: Whether to enable write operations

    Returns:
        Tuple of (Server instance, Toolset, ResourceSet)
    """
    server = Server("ldap-mcp")

    toolset = Toolset(client)
    resource_set = ResourceSet(client)

    # Register list_tools handler
    @server.list_tools()
    async def list_tools_handler():
        return toolset.get_tools(read_write)

    # Register call_tool handler
    @server.call_tool()
    async def call_tool_handler(name: str, arguments: Any) -> list:
        return await toolset.handle_tool(name, arguments or {})

    # Register list_resources handler
    @server.list_resources()
    async def list_resources_handler():
        return resource_set.get_resources()

    # Register list_resource_templates handler
    @server.list_resource_templates()
    async def list_resource_templates_handler():
        return resource_set.get_resource_templates()

    # Register read_resource handler
    @server.read_resource()
    async def read_resource_handler(uri: str):
        return await resource_set.handle_resource(uri)

    log.info(f"MCP server created with {len(toolset.get_tools(read_write))} tools")
    return server, toolset, resource_set


def serve(cfg: dict) -> int:
    """
    Main entry point to start the MCP server.

    Args:
        cfg: Configuration dictionary

    Returns:
        Exit code
    """
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
    addr = cfg.get('addr', ':8080')

    # Parse address
    if addr.startswith(':'):
        host = '0.0.0.0'
        port = int(addr[1:])
    else:
        parts = addr.rsplit(':', 1)
        host = parts[0] if len(parts) > 1 else '0.0.0.0'
        port = int(parts[1]) if len(parts) > 1 else 8080

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

    available_tools = "search_entries, get_entry"
    if read_write:
        available_tools += ", add_entry, modify_entry, delete_entry"
    log.info(f"Available tools: {available_tools}")
    log.info("Available resources: ldap://root-dse, ldap://entry/{{dn}}")

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
    except Exception as e:
        log.error(f"Failed to connect to LDAP server: {e}")
        return 1

    # Create MCP server
    app_server, toolset, resource_set = create_mcp_server(ldap_client, read_write)

    # Create Starlette app for SSE
    async def handle_sse(request: Request) -> Response:
        """Handle SSE connections."""
        async with SseServerTransport("/messages") as (read_stream, write_stream):
            await app_server.run(
                read_stream,
                write_stream,
                app_server.create_initialization_options(),
            )
        return Response("SSE connection closed", status_code=200)

    async def handle_messages(request: Request) -> Response:
        """Handle POST messages."""
        return Response('{"status": "ok"}', media_type="application/json")

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ],
    )

    # Run server
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        log.info("Received shutdown signal")
    except Exception as e:
        log.error(f"Server error: {e}", exc_info=True)
        return 1
    finally:
        if ldap_client:
            ldap_client.close()
        log.info("Server shutdown complete")

    return 0


__all__ = ['serve']

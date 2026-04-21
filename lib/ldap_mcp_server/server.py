"""Main server module for LDAP MCP Server.

This module provides the serve() entry point that:
1. Connects to LDAP using credentials from config
2. Builds the FastMCP server instance
3. Registers tools and resources
4. Starts the appropriate transport (stdio or SSE)
"""

import logging
import uvicorn
from mcp.server.fastmcp import FastMCP
from ldap_mcp_server.config import Config
from ldap_mcp_server.ldap_client import LDAPClient
from ldap_mcp_server.tools import register_tools
from ldap_mcp_server.resources import register_resources

log = logging.getLogger(__name__)


def serve(cfg: Config) -> int:
    """Main entry point for LDAP MCP Server.

    Initializes LDAP client, builds the MCP server, registers tools and resources,
    then starts the appropriate transport.

    Critical wiring order:
    1. Connect to LDAP
    2. Build FastMCP instance
    3. Register tools and resources (BEFORE getting app or running)
    4. Get ASGI app or run stdio transport
    5. Wrap with middleware if needed (SSE only)
    6. Start server

    Args:
        cfg: Configuration object with all settings

    Returns:
        0 on clean exit, 1 on error
    """
    # 1. Connect to LDAP
    try:
        client = LDAPClient(
            url=cfg.url,
            bind_dn=cfg.bind_dn,
            bind_password=cfg.bind_password,
            use_starttls=cfg.use_starttls,
            insecure_tls=cfg.insecure_tls,
            default_timeout=cfg.timeout,
        )
        log.info('Connected to LDAP: %s', cfg.url)
    except Exception as e:
        log.error('Failed to connect to LDAP: %s', e)
        return 1

    # 2. Build the MCP server
    mcp = FastMCP(name='ldap-mcp')

    # 3. Register tools and resources BEFORE getting the app or running
    register_tools(mcp, client, cfg.read_write)
    register_resources(mcp, client)

    mode = 'read-write' if cfg.read_write else 'read-only'
    log.info('Transport: %s | Mode: %s', cfg.transport, mode)

    # 4. Dispatch transport
    try:
        if cfg.transport == 'stdio':
            log.info('Starting stdio transport')
            mcp.run(transport='stdio')

        else:  # sse
            app = mcp.sse_app()

            # Wrap with API key auth at the ASGI level.
            # IMPORTANT: Use direct instantiation — NOT app.add_middleware().
            if cfg.api_key:
                from ldap_mcp_server.middleware import APIKeyMiddleware
                app = APIKeyMiddleware(app, api_key=cfg.api_key)
                log.info('API key authentication enabled')
            else:
                log.warning('No LDAP_MCP_SERVER_API_KEY set — server accepts all connections')

            log.info('SSE endpoint: http://%s:%d/sse', cfg.host, cfg.port)
            log.info('Messages endpoint: http://%s:%d/messages', cfg.host, cfg.port)

            uvicorn.run(
                app,
                host=cfg.host,
                port=cfg.port,
                log_level=cfg.log_level.lower(),
            )

        return 0

    except KeyboardInterrupt:
        log.info('Shutdown signal received')
        return 0
    except Exception as e:
        log.error('Server error: %s', e, exc_info=True)
        return 1
    finally:
        try:
            client.close()
        except Exception:
            pass
        log.info('Server stopped')


__all__ = ['serve']

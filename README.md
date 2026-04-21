# LDAP MCP Server (Python)

LDAP MCP Server exposes an LDAP directory through the Model Context Protocol (MCP), enabling MCP
clients to run common directory searches and CRUD operations using the standard tool/resource
workflow.

This is a Python implementation of the [LDAP MCP Server](https://github.com/trxo/ldap-mcp)
originally written in Go.

## Features

- Search, retrieve, add, modify, and delete LDAP entries through MCP tools.
- Optional read-only mode that limits MCP clients to safe operations.
- Support for StartTLS upgrades, LDAPS endpoints, and configurable TLS verification.
- Built-in MCP resources for the directory root DSE and arbitrary entries by DN.
- Graceful shutdown handling and automatic LDAP reconnection logic.
- Environment variable support via `.env` files with python-dotenv.

## Requirements
- Python 3.11 or newer
- Access to an LDAP server (OpenLDAP, Active Directory, etc.)
- MCP client capable of speaking the SSE transport (e.g., Claude Desktop, OpenCode, etc.)

## Installation

Install using pip:

```bash
pip install kizano-mcp-ldap-server
```

Or install from source:

```bash
cd ldap-mcp.py
pip install -e .
```

## Running the Server

Basic usage:

```bash
ldap-mcp-server \
  --host 0.0.0.0 \
  --port 9090 \
  --url ldap://localhost:389 \
  --bind-dn "cn=admin,dc=example,dc=com" \
  --bind-password secret
```

The server will start and listen for HTTP/SSE connections on the specified host and port.

You should see output like:
```
2026-04-21 11:00:00 INFO: Starting LDAP MCP Server on 0.0.0.0:9090 (read-only mode)
2026-04-21 11:00:00 INFO: LDAP URL: ldap://localhost:389
2026-04-21 11:00:00 INFO: Connected to LDAP server successfully
2026-04-21 11:00:00 INFO: Available tools: search_entries, get_entry
2026-04-21 11:00:00 INFO: SSE endpoint: http://0.0.0.0:9090/sse
2026-04-21 11:00:00 INFO: Messages endpoint: http://0.0.0.0:9090/messages
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:9090 (Press CTRL+C to quit)
```

### Command-Line Flags

- `--host`: Host to bind to (default `0.0.0.0`, overridable via `MCP_HOST` env var).
- `--port`: Port to listen on (default `9090`, overridable via `MCP_PORT` env var).
- `--url`: LDAP server URL such as `ldap://host:389` or `ldaps://host:636`.
- `--bind-dn`: Distinguished name used for LDAP bind.
- `--bind-password`: Password for LDAP bind (or use `LDAP_BIND_PASSWORD` environment variable).
- `--starttls`: Upgrade a plain LDAP connection to TLS. Only valid when using `ldap://` URLs.
- `--insecure`: Skip TLS certificate verification (useful for testing with self-signed certs).
- `--read-write`: Enable add/modify/delete tools. If omitted the server operates in read-only mode.
- `--timeout`: Per-request timeout when talking to the LDAP server in seconds (default 30).
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

Use `--help` to print the full list of flags.

### Environment Variables

The server supports loading configuration from a `.env` file in the current directory:

```env
# .env file example
MCP_HOST=0.0.0.0
MCP_PORT=9090
LDAP_URI=ldap://localhost:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=secret
LOG_LEVEL=INFO
```

Environment variables:
- `MCP_HOST`: Host to bind to (overrides `--host` flag)
- `MCP_PORT`: Port to listen on (overrides `--port` flag)
- `LDAP_URI`: LDAP server URL (overrides `--url` flag)
- `LDAP_BIND_DN`: Bind DN (overrides `--bind-dn` flag)
- `LDAP_BIND_PASSWORD`: Bind password (alternative to `--bind-password`)
- `LOG_LEVEL`: Logging level

### Examples

Connect to LDAP with StartTLS:

```bash
ldap-mcp-server \
  --url ldap://127.0.0.1:389 \
  --bind-dn "cn=admin,dc=example,dc=com" \
  --bind-password secret \
  --starttls
```

Connect to LDAPS on custom port:
```bash
ldap-mcp-server \
  --host 0.0.0.0 \
  --port 9000 \
  --url ldaps://ldap.example.com:636 \
  --bind-dn "cn=service,dc=example,dc=com" \
  --read-write
```

Using a `.env` file:

```bash
# Create .env with credentials
echo "LDAP_BIND_PASSWORD=secret" > .env

# Run server
ldap-mcp-server \
  --url ldap://localhost:389 \
  --bind-dn "cn=admin,dc=example,dc=com"
```

## MCP Surface

### Tools

- `search_entries`: Execute LDAP searches with paging, scope selection, alias dereferencing,
  and size limits.
- `get_entry`: Fetch a single entry by distinguished name.
- `add_entry`: Create new entries (requires `--read-write`).
- `modify_entry`: Apply attribute modifications (requires `--read-write`).
- `delete_entry`: Delete entries (requires `--read-write`).

### Resources

- `ldap://root-dse`: Returns the directory root DSE as JSON.
- `ldap://entry/{dn}`: Fetches a specific entry when provided with a DN.

## Development

### Setup Development Environment

```bash
cd ldap-mcp.py

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .
```

### Project Structure

```tree
ldap-mcp.py/
├── lib/
│   └── ldap_mcp_server/
│       ├── __init__.py        # Main entry point with dotenv loading
│       ├── __main__.py        # Module execution entry
│       ├── cli.py             # Command-line argument parsing
│       ├── server.py          # MCP server with SSE transport
│       ├── ldap_client.py     # LDAP connection and operations
│       ├── tools.py           # MCP tool handlers
│       └── resources.py       # MCP resource handlers
├── pyproject.toml             # Package configuration
└── README.md
```

### Architecture

The Python implementation closely mirrors the Go version:

- **ldap_client.py**: Thread-safe LDAP client with connection pooling, StartTLS support, and
  automatic reconnection on errors. Uses `ldap3` library.
- **tools.py**: Exposes LDAP operations as MCP tools, validating inputs and converting between
  MCP and LDAP formats.
- **resources.py**: Provides MCP resources for root DSE and entry lookups by DN.
- **server.py**: Main MCP server implementation using SSE transport via Starlette/Uvicorn.

## Comparison with Go Version

This Python implementation provides feature parity with the original Go version:

| Feature | Go | Python |
|---------|----|----|
| LDAP Search | ✅ | ✅ |
| Get/Add/Modify/Delete | ✅ | ✅ |
| StartTLS Support | ✅ | ✅ |
| LDAPS Support | ✅ | ✅ |
| Read-only Mode | ✅ | ✅ |
| Auto-reconnect | ✅ | ✅ |
| Root DSE Resource | ✅ | ✅ |
| Entry Resources | ✅ | ✅ |
| SSE Transport | ✅ | ✅ |
| Environment Variables | ✅ | ✅ |
| `.env` File Support | ❌ | ✅ |

## Connecting MCP Clients

Once the server is running, you can connect MCP clients to it:

### HTTP/SSE Endpoints

- **SSE Connection:** `GET http://localhost:9090/sse`
- **Post Messages:** `POST http://localhost:9090/messages`

### Example Client Configuration (Claude Desktop)

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "ldap": {
      "url": "http://localhost:9090/sse"
    }
  }
}
```

## License

Same license as the original LDAP MCP Server.

## Contributing

Contributions are welcome! Please ensure:

- Code follows PEP 8 style guidelines
- All imports are at the module level (no JIT imports)
- No unused imports, functions, or variables
- DRY principles are followed

## Acknowledgments

This is a Python port of the [LDAP MCP Server](https://github.com/trxo/ldap-mcp) by trxo.

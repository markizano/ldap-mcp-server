# LDAP MCP Server

A Python-based [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes LDAP directory operations to AI agents and coding assistants like Claude, Cursor, and OpenCode.

This is a Python port of the original [trxo/ldap-mcp](https://github.com/trxo/ldap-mcp) implementation written in Go by [@trxo](https://github.com/trxo). Full credit to the original author for the design and concept.

## Features

- **Full LDAP CRUD operations** - Search, read, add, modify, and delete directory entries
- **Dual transport modes** - stdio (local) and SSE (networked)
- **LDIF and JSON output** - RFC 2849 compliant LDIF formatting or structured JSON
- **API key authentication** - Secure Bearer token or X-API-Key header validation (SSE mode)
- **Read-only or read-write** - Control write access via `--read-write` flag
- **TLS support** - LDAPS and StartTLS with certificate validation
- **MCP resources** - Expose Root DSE and individual entries as resources
- **Comprehensive tests** - 50+ unit tests with full coverage

## Installation

### From PyPI (when published)

```bash
pip install kizano-ldap-mcp-server
```

### From Source

```bash
git clone https://github.com/markizano/ldap-mcp-server.git
cd ldap-mcp-server
pip install -e .
```

### Using uv (recommended)

```bash
git clone https://github.com/markizano/ldap-mcp-server.git
cd ldap-mcp-server
uv pip install -e .
```

## Quick Start

### 1. Configuration

Create a `.env` file (copy from `.env.example`):

```bash
# LDAP connection
LDAP_URI=ldap://localhost:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=your_password_here

# MCP server (SSE mode)
MCP_HOST=0.0.0.0
MCP_PORT=9090
LDAP_MCP_SERVER_API_KEY=your-secure-api-key-here

# Logging
LOG_LEVEL=INFO
```

### 2. Start the Server

**stdio mode (local development, no API key needed):**

```bash
ldap-mcp-server --transport stdio --read-write
```

**SSE mode (network server with authentication):**

```bash
ldap-mcp-server --transport sse --host 0.0.0.0 --port 9090
```

### 3. Configure Your MCP Client

**For stdio mode (Claude Desktop, Cursor, OpenCode):**

Add to your MCP client configuration (e.g., `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "ldap": {
      "command": "ldap-mcp-server",
      "args": ["--transport", "stdio", "--read-write"],
      "env": {
        "LDAP_URI": "ldap://localhost:389",
        "LDAP_BIND_DN": "cn=admin,dc=example,dc=com",
        "LDAP_BIND_PASSWORD": "your_password_here"
      }
    }
  }
}
```

**For SSE mode (remote server):**

```json
{
  "mcpServers": {
    "ldap": {
      "url": "http://your-server:9090/sse",
      "headers": {
        "Authorization": "Bearer YOUR_LDAP_MCP_SERVER_API_KEY"
      }
    }
  }
}
```

## Usage

### Available Tools

The server exposes the following MCP tools:

#### `search_entries`
Search for LDAP entries matching a filter.

```python
search_entries(
    base_dn="ou=users,dc=example,dc=com",
    filter="(objectClass=inetOrgPerson)",
    scope="sub",  # base, one, or sub
    attributes=["cn", "mail", "uid"],  # None for all attributes
    output_format="ldif"  # ldif or json
)
```

#### `get_entry`
Retrieve a single entry by DN.

```python
get_entry(
    dn="uid=jsmith,ou=users,dc=example,dc=com",
    attributes=["cn", "mail"],
    output_format="ldif"
)
```

#### `add_entry` (requires `--read-write`)
Create a new LDAP entry.

```python
add_entry(
    dn="uid=newuser,ou=users,dc=example,dc=com",
    attributes={
        "objectClass": ["inetOrgPerson", "organizationalPerson"],
        "cn": ["New User"],
        "sn": ["User"],
        "mail": ["newuser@example.com"]
    }
)
```

#### `modify_entry` (requires `--read-write`)
Modify an existing entry.

```python
modify_entry(
    dn="uid=jsmith,ou=users,dc=example,dc=com",
    changes=[
        {
            "operation": "replace",
            "attribute": "mail",
            "values": ["newemail@example.com"]
        }
    ]
)
```

#### `delete_entry` (requires `--read-write`)
Delete an entry.

```python
delete_entry(dn="uid=olduser,ou=users,dc=example,dc=com")
```

### Available Resources

#### `ldap://root-dse`
Server metadata and capabilities (JSON format).

#### `ldap://entry/{url-encoded-dn}`
Individual entry by DN (LDIF format).

Example: `ldap://entry/uid%3Djsmith%2Cou%3Dusers%2Cdc%3Dexample%2Cdc%3Dcom`

## Command-Line Options

```
usage: ldap-mcp-server [-h] [--transport {stdio,sse}] [--host HOST]
                       [--port PORT] [--url URL] [--bind-dn BIND_DN]
                       [--bind-password BIND_PASSWORD] [--starttls]
                       [--insecure] [--read-write] [--timeout TIMEOUT]
                       [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

options:
  --transport {stdio,sse}    Transport mode (default: sse)
  --host HOST                Host to bind to (default: 0.0.0.0)
  --port PORT                Port to listen on (default: 9090)
  --url URL                  LDAP server URL
  --bind-dn BIND_DN          Bind DN for service account
  --bind-password BIND_PASSWORD
                             Bind password
  --starttls                 Use StartTLS (cannot be used with ldaps://)
  --insecure                 Skip TLS certificate verification (INSECURE)
  --read-write               Enable write operations
  --timeout TIMEOUT          LDAP operation timeout in seconds (default: 30)
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                             Logging level (default: INFO)
```

CLI flags override environment variables.

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=ldap_mcp_server --cov-report=html
```

### Project Structure

```
ldap-mcp.py/
├── lib/ldap_mcp_server/
│   ├── __init__.py         # Entry point with dotenv loading
│   ├── __main__.py         # python -m support
│   ├── cli.py              # Argument parsing
│   ├── config.py           # Configuration dataclass
│   ├── ldap_client.py      # LDAP connection wrapper
│   ├── ldif.py             # LDIF formatter (RFC 2849)
│   ├── middleware.py       # API key authentication
│   ├── resources.py        # MCP resource registrations
│   ├── server.py           # Main serve() function
│   └── tools.py            # MCP tool registrations
├── tests/
│   ├── test_config.py      # Configuration tests
│   ├── test_ldif.py        # LDIF formatting tests
│   └── test_middleware.py  # Authentication tests
├── pyproject.toml          # Package metadata
└── pytest.ini              # Test configuration
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality (maintain >90% coverage)
3. **Follow the coding style:**
   - Use type hints for all function signatures
   - All imports at the top of the module (no JIT imports)
   - Follow DRY principles (no copy-paste code)
   - Docstrings for all public functions
4. **Run the test suite** before submitting:
   ```bash
   pytest tests/ -v
   ```
5. **Update documentation** if adding features
6. **Submit a pull request** with a clear description

### Development Setup

```bash
# Clone the repo
git clone https://github.com/markizano/ldap-mcp-server.git
cd ldap-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install in editable mode with test dependencies
pip install -e ".[test]"

# Run tests
pytest tests/ -v
```

## Security

- **API keys** are read from environment variables only, never from CLI or config files
- **TLS certificate validation** is enabled by default (use `--insecure` to disable for testing)
- **Write operations** are disabled by default (requires explicit `--read-write` flag)
- **Bind credentials** should use service accounts with minimal required privileges

**Warning:** Never commit `.env` files or hardcode credentials in code.

## License

MIT License - see LICENSE file for details

## Credits

- **Original Implementation:** [trxo/ldap-mcp](https://github.com/trxo/ldap-mcp) by [@trxo](https://github.com/trxo) - Go implementation
- **Python Port:** [@markizano](https://github.com/markizano)
- **MCP Protocol:** [Anthropic](https://modelcontextprotocol.io)

## Troubleshooting

### "Failed to connect to LDAP"
- Verify `LDAP_URI` is correct (`ldap://` or `ldaps://`)
- Check firewall rules allow connections to LDAP port (389 or 636)
- Test with `ldapsearch` to verify credentials

### "401 Unauthorized" (SSE mode)
- Ensure `LDAP_MCP_SERVER_API_KEY` is set in environment
- Verify client is sending `Authorization: Bearer <key>` or `X-API-Key: <key>` header
- Check server logs for auth attempts

### "405 Method Not Allowed"
- Client may be POSTing to `/sse` instead of `/messages`
- Client URL should be `http://host:port/sse` (not `/messages`)

### Write operations fail
- Ensure server started with `--read-write` flag
- Verify bind DN has write permissions in LDAP directory
- Check LDAP server logs for permission errors

## Support

- **Issues:** https://github.com/markizano/ldap-mcp-server/issues
- **Discussions:** https://github.com/markizano/ldap-mcp-server/discussions
- **Original Go version:** https://github.com/trxo/ldap-mcp

## Roadmap

- [ ] Connection pooling for high-traffic deployments
- [ ] Schema introspection and validation
- [ ] LDAP server discovery (DNS SRV records)
- [ ] Prometheus metrics endpoint
- [ ] Docker image and Kubernetes manifests
- [ ] Interactive schema browser MCP resource

---

**Made with ❤️ for the MCP community**

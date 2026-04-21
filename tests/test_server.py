#!/usr/bin/env python3
"""
Quick test to verify the server can start.
This doesn't connect to a real LDAP server.
"""

import asyncio
import sys

async def test_server_import():
    """Test that we can import the server module."""
    try:
        from lib.ldap_mcp_server import server
        print("✓ Server module imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import server: {e}")
        return False

async def test_fastmcp():
    """Test that FastMCP is available."""
    try:
        from mcp.server.fastmcp import FastMCP
        
        # Create a minimal test server
        mcp = FastMCP(
            name="test",
            host="127.0.0.1",
            port=19999,  # Use high port for testing
        )
        
        @mcp.tool()
        async def test_tool(input: str) -> str:
            """Test tool."""
            return f"Echo: {input}"
        
        print("✓ FastMCP server created successfully")
        tools = await mcp.list_tools()
        print(f"  - Tools registered: {len(tools)}")
        return True
    except Exception as e:
        print(f"✗ Failed to create FastMCP server: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("Testing LDAP MCP Server components...\n")
    
    results = []
    results.append(await test_server_import())
    results.append(await test_fastmcp())
    
    print("\n" + "="*50)
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""
MCP tools for LDAP operations.

This module exposes LDAP search and CRUD operations as MCP tools.
"""

import json
from typing import List, Dict, Any

from mcp.types import Tool, TextContent
from kizano import getLogger

from ldap_mcp_server.ldap_client import (
    LDAPClient,
    LDAPNotFoundError,
    SearchScope,
    DerefAliases,
)

log = getLogger(__name__)


class Toolset:
    """Manages MCP tools for LDAP operations."""

    def __init__(self, client: LDAPClient):
        """
        Initialize toolset.

        Args:
            client: LDAP client instance
        """
        self.client = client

    def get_tools(self, read_write: bool) -> List[Tool]:
        """
        Get list of MCP tools.

        Args:
            read_write: Whether to include write operations

        Returns:
            List of Tool definitions
        """
        tools = [
            self._search_entries_tool(),
            self._get_entry_tool(),
        ]

        if read_write:
            tools.extend([
                self._add_entry_tool(),
                self._modify_entry_tool(),
                self._delete_entry_tool(),
            ])

        return tools

    def _search_entries_tool(self) -> Tool:
        """Define search_entries tool."""
        return Tool(
            name="search_entries",
            description="Execute an LDAP search operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_dn": {
                        "type": "string",
                        "description": "Base distinguished name for the search",
                    },
                    "filter": {
                        "type": "string",
                        "description": "LDAP search filter (RFC 4515)",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Search scope: base, one, or sub",
                        "enum": ["base", "one", "sub"],
                        "default": "sub",
                    },
                    "attributes": {
                        "type": "array",
                        "description": "Attributes to return; empty array returns all",
                        "items": {"type": "string"},
                    },
                    "size_limit": {
                        "type": "number",
                        "description": "Maximum number of entries to return (0 means server default)",
                        "minimum": 0,
                    },
                    "types_only": {
                        "type": "boolean",
                        "description": "Return only attribute types without values",
                    },
                    "page_size": {
                        "type": "number",
                        "description": "Optional Simple Paged Results size (0 disables paging)",
                        "minimum": 0,
                    },
                    "deref_aliases": {
                        "type": "string",
                        "description": "Alias dereferencing strategy: never, searching, finding, or always",
                        "enum": ["never", "searching", "finding", "always"],
                        "default": "never",
                    },
                },
                "required": ["base_dn", "filter"],
            },
        )

    def _get_entry_tool(self) -> Tool:
        """Define get_entry tool."""
        return Tool(
            name="get_entry",
            description="Retrieve a single LDAP entry by DN",
            inputSchema={
                "type": "object",
                "properties": {
                    "dn": {
                        "type": "string",
                        "description": "The distinguished name of the entry",
                    },
                    "attributes": {
                        "type": "array",
                        "description": "Attributes to return; empty array returns all",
                        "items": {"type": "string"},
                    },
                },
                "required": ["dn"],
            },
        )

    def _add_entry_tool(self) -> Tool:
        """Define add_entry tool."""
        return Tool(
            name="add_entry",
            description="Create a new LDAP entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "dn": {
                        "type": "string",
                        "description": "Distinguished name for the new entry",
                    },
                    "attributes": {
                        "type": "object",
                        "description": "Map of attribute names to string arrays",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "required": ["dn", "attributes"],
            },
        )

    def _modify_entry_tool(self) -> Tool:
        """Define modify_entry tool."""
        return Tool(
            name="modify_entry",
            description="Modify attributes of an LDAP entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "dn": {
                        "type": "string",
                        "description": "The distinguished name of the entry",
                    },
                    "changes": {
                        "type": "array",
                        "description": "List of attribute modifications",
                        "items": {
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "enum": ["add", "replace", "delete"],
                                    "description": "Modification operation",
                                },
                                "attribute": {
                                    "type": "string",
                                    "description": "Attribute name",
                                },
                                "values": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Attribute values (ignored for delete)",
                                },
                            },
                            "required": ["operation", "attribute"],
                        },
                    },
                },
                "required": ["dn", "changes"],
            },
        )

    def _delete_entry_tool(self) -> Tool:
        """Define delete_entry tool."""
        return Tool(
            name="delete_entry",
            description="Delete an LDAP entry by DN",
            inputSchema={
                "type": "object",
                "properties": {
                    "dn": {
                        "type": "string",
                        "description": "The distinguished name to delete",
                    },
                },
                "required": ["dn"],
            },
        )

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle MCP tool invocations.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of TextContent results
        """
        try:
            if name == "search_entries":
                return await self._handle_search_entries(arguments)
            elif name == "get_entry":
                return await self._handle_get_entry(arguments)
            elif name == "add_entry":
                return await self._handle_add_entry(arguments)
            elif name == "modify_entry":
                return await self._handle_modify_entry(arguments)
            elif name == "delete_entry":
                return await self._handle_delete_entry(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            log.error(f"Tool {name} error: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_search_entries(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle search_entries tool."""
        base_dn = args.get("base_dn", "").strip()
        filter_string = args.get("filter", "").strip()

        if not base_dn:
            return [TextContent(type="text", text="Error: base_dn parameter is required")]
        if not filter_string:
            return [TextContent(type="text", text="Error: filter parameter is required")]

        scope_str = args.get("scope", "sub").lower()
        try:
            scope = SearchScope(scope_str)
        except ValueError:
            return [TextContent(type="text", text="Error: scope must be one of base, one, or sub")]

        attributes = args.get("attributes", [])
        if not attributes:
            attributes = None

        size_limit = max(0, args.get("size_limit", 0))
        page_size = max(0, min(args.get("page_size", 0), 2**32 - 1))
        types_only = args.get("types_only", False)

        deref_str = args.get("deref_aliases", "never").lower()
        try:
            deref = DerefAliases(deref_str)
        except ValueError:
            return [TextContent(type="text", text="Error: deref_aliases must be one of never, searching, finding, or always")]

        try:
            entries = self.client.search(
                base_dn=base_dn,
                filter_string=filter_string,
                scope=scope,
                attributes=attributes,
                size_limit=size_limit,
                types_only=types_only,
                deref_aliases=deref,
                page_size=page_size,
            )

            payload = {
                "entries": entries,
                "count": len(entries),
            }

            result_text = f"LDAP search succeeded\n```json\n{json.dumps(payload, indent=2)}\n```"
            return [TextContent(type="text", text=result_text)]

        except LDAPNotFoundError as e:
            return [TextContent(type="text", text=f"Error: LDAP entry not found - {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_entry(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get_entry tool."""
        dn = args.get("dn", "").strip()
        if not dn:
            return [TextContent(type="text", text="Error: dn parameter is required")]

        attributes = args.get("attributes", [])
        if not attributes:
            attributes = None

        try:
            entry = self.client.get_entry(dn, attributes)
            payload = {"entry": entry}
            result_text = f"LDAP entry retrieved\n```json\n{json.dumps(payload, indent=2)}\n```"
            return [TextContent(type="text", text=result_text)]

        except LDAPNotFoundError:
            return [TextContent(type="text", text="Error: LDAP entry not found")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_add_entry(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle add_entry tool."""
        dn = args.get("dn", "").strip()
        if not dn:
            return [TextContent(type="text", text="Error: dn parameter is required")]

        attributes = args.get("attributes", {})
        if not attributes or not isinstance(attributes, dict):
            return [TextContent(type="text", text="Error: attributes must be an object mapping attribute names to arrays")]

        # Validate attributes structure
        for attr_name, attr_values in attributes.items():
            if not isinstance(attr_values, list):
                return [TextContent(type="text", text=f"Error: attribute {attr_name} must be an array")]
            for val in attr_values:
                if not isinstance(val, str):
                    return [TextContent(type="text", text=f"Error: all values for {attr_name} must be strings")]

        try:
            self.client.add_entry(dn, attributes)
            return [TextContent(type="text", text=f"Entry {dn} created successfully")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_modify_entry(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle modify_entry tool."""
        dn = args.get("dn", "").strip()
        if not dn:
            return [TextContent(type="text", text="Error: dn parameter is required")]

        changes = args.get("changes", [])
        if not changes or not isinstance(changes, list):
            return [TextContent(type="text", text="Error: changes must be a non-empty array")]

        # Validate changes
        modifications = []
        for i, change in enumerate(changes):
            if not isinstance(change, dict):
                return [TextContent(type="text", text=f"Error: change at index {i} must be an object")]

            operation = change.get("operation", "").strip().lower()
            attribute = change.get("attribute", "").strip()

            if not operation or not attribute:
                return [TextContent(type="text", text=f"Error: change at index {i} must include operation and attribute")]

            values = change.get("values", [])
            if not isinstance(values, list):
                values = []

            modifications.append({
                "operation": operation,
                "attribute": attribute,
                "values": values,
            })

        try:
            self.client.modify_entry(dn, modifications)
            return [TextContent(type="text", text=f"Entry {dn} modified successfully")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_delete_entry(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle delete_entry tool."""
        dn = args.get("dn", "").strip()
        if not dn:
            return [TextContent(type="text", text="Error: dn parameter is required")]

        try:
            self.client.delete_entry(dn)
            return [TextContent(type="text", text=f"Entry {dn} deleted successfully")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


__all__ = ['Toolset']

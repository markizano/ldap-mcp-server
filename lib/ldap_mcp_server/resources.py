"""
MCP resources for LDAP directory access.

This module exposes LDAP directory resources through MCP.
"""

import json
from typing import List
from urllib.parse import quote, unquote

from mcp.types import Resource, ResourceTemplate, ResourceContents, TextResourceContents
from kizano import getLogger

from ldap_mcp_server.ldap_client import LDAPClient, LDAPNotFoundError

log = getLogger(__name__)


class ResourceSet:
    """Manages MCP resources for LDAP directory."""

    def __init__(self, client: LDAPClient):
        """
        Initialize resource set.

        Args:
            client: LDAP client instance
        """
        self.client = client

    def get_resources(self) -> List[Resource]:
        """
        Get list of static MCP resources.

        Returns:
            List of Resource definitions
        """
        return [
            Resource(
                uri="ldap://root-dse",
                name="LDAP Root DSE",
                description="Root DSE attributes for the LDAP server",
                mimeType="application/json",
            )
        ]

    def get_resource_templates(self) -> List[ResourceTemplate]:
        """
        Get list of resource templates.

        Returns:
            List of ResourceTemplate definitions
        """
        return [
            ResourceTemplate(
                uriTemplate="ldap://entry/{dn}",
                name="LDAP Entry",
                description="Retrieve an LDAP entry by DN (URL-escaped)",
                mimeType="application/json",
            )
        ]

    async def handle_resource(self, uri: str) -> List[ResourceContents]:
        """
        Handle resource requests.

        Args:
            uri: Resource URI

        Returns:
            List of ResourceContents
        """
        try:
            if uri == "ldap://root-dse":
                return await self._handle_root_dse()
            elif uri.startswith("ldap://entry/"):
                dn_encoded = uri[len("ldap://entry/"):]
                dn = self._decode_dn(dn_encoded)
                return await self._handle_entry(dn)
            else:
                raise ValueError(f"Unknown resource URI: {uri}")

        except Exception as e:
            log.error(f"Resource handler error for {uri}: {e}", exc_info=True)
            raise

    async def _handle_root_dse(self) -> List[ResourceContents]:
        """Handle root DSE resource request."""
        try:
            entry = self.client.read_root_dse(attributes=None)
            payload = {"root_dse": entry}

            json_text = json.dumps(payload, indent=2)

            return [
                TextResourceContents(
                    uri="ldap://root-dse",
                    mimeType="application/json",
                    text=json_text,
                )
            ]

        except Exception as e:
            log.error(f"Failed to read root DSE: {e}")
            raise

    async def _handle_entry(self, dn: str) -> List[ResourceContents]:
        """
        Handle LDAP entry resource request.

        Args:
            dn: Distinguished name

        Returns:
            List of ResourceContents
        """
        try:
            entry = self.client.get_entry(dn, attributes=None)
            payload = {"entry": entry}

            json_text = json.dumps(payload, indent=2)

            # Re-encode the DN for the URI
            uri = f"ldap://entry/{quote(entry['dn'], safe='')}"

            return [
                TextResourceContents(
                    uri=uri,
                    mimeType="application/json",
                    text=json_text,
                )
            ]

        except LDAPNotFoundError:
            raise ValueError(f"LDAP entry not found: {dn}")
        except Exception as e:
            log.error(f"Failed to read entry {dn}: {e}")
            raise

    def _decode_dn(self, encoded: str) -> str:
        """
        Decode URL-encoded DN.

        Args:
            encoded: URL-encoded DN

        Returns:
            Decoded DN

        Raises:
            ValueError: If DN is invalid
        """
        try:
            dn = unquote(encoded)
            if not dn.strip():
                raise ValueError("DN cannot be empty")
            return dn
        except Exception as e:
            raise ValueError(f"Invalid DN encoding: {e}")


__all__ = ['ResourceSet']

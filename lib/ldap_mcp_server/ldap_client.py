"""
LDAP client wrapper providing connection management and CRUD operations.

This module provides a thread-safe LDAP client with automatic reconnection,
StartTLS support, and comprehensive error handling.
"""

import ssl
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from threading import Lock
from enum import Enum

from ldap3 import Server, Connection, Tls, ALL, SUBTREE, BASE, LEVEL
from ldap3.core.exceptions import LDAPException
from kizano import getLogger

log = getLogger(__name__)


class LDAPNotFoundError(Exception):
    """Raised when an LDAP entry is not found."""
    pass


class SearchScope(str, Enum):
    """LDAP search scope options."""
    BASE = "base"
    ONE = "one"
    SUB = "sub"

    def to_ldap_scope(self) -> str:
        """Convert to ldap3 scope constant."""
        if self == SearchScope.BASE:
            return BASE
        elif self == SearchScope.ONE:
            return LEVEL
        else:
            return SUBTREE


class DerefAliases(str, Enum):
    """LDAP alias dereferencing strategies."""
    NEVER = "never"
    SEARCHING = "searching"
    FINDING = "finding"
    ALWAYS = "always"

    def to_ldap_deref(self) -> str:
        """Convert to ldap3 dereference constant."""
        from ldap3 import DEREF_NEVER, DEREF_SEARCH, DEREF_BASE, DEREF_ALWAYS
        if self == DerefAliases.SEARCHING:
            return DEREF_SEARCH
        elif self == DerefAliases.FINDING:
            return DEREF_BASE
        elif self == DerefAliases.ALWAYS:
            return DEREF_ALWAYS
        else:
            return DEREF_NEVER


class ModifyOperation(str, Enum):
    """LDAP modify operation types."""
    ADD = "add"
    REPLACE = "replace"
    DELETE = "delete"


class LDAPClient:
    """Thread-safe LDAP client with connection pooling and auto-reconnect."""

    def __init__(
        self,
        url: str,
        bind_dn: str = "",
        bind_password: str = "",
        use_starttls: bool = False,
        insecure_tls: bool = False,
        default_timeout: int = 30,
    ):
        """
        Initialize LDAP client.

        Args:
            url: LDAP server URL (ldap://... or ldaps://...)
            bind_dn: Distinguished name for binding
            bind_password: Password for binding
            use_starttls: Whether to use StartTLS
            insecure_tls: Skip TLS certificate verification
            default_timeout: Default timeout in seconds
        """
        self.url = url
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.use_starttls = use_starttls
        self.insecure_tls = insecure_tls
        self.default_timeout = default_timeout if default_timeout > 0 else 30

        self._conn: Optional[Connection] = None
        self._lock = Lock()

        # Initialize connection
        self._connect()

    def _connect(self) -> None:
        """Establish connection to LDAP server."""
        parsed = urlparse(self.url)
        host = parsed.hostname
        port = parsed.port or (636 if parsed.scheme == "ldaps" else 389)
        use_ssl = parsed.scheme == "ldaps"

        # Configure TLS
        tls_config = None
        if use_ssl or self.use_starttls:
            tls_args = {}
            if self.insecure_tls:
                tls_args['validate'] = ssl.CERT_NONE
            else:
                tls_args['validate'] = ssl.CERT_REQUIRED
            tls_config = Tls(**tls_args)

        # Create server
        server = Server(
            host,
            port=port,
            use_ssl=use_ssl,
            tls=tls_config,
            get_info=ALL,
            connect_timeout=self.default_timeout,
        )

        # Create connection
        self._conn = Connection(
            server,
            user=self.bind_dn if self.bind_dn else None,
            password=self.bind_password if self.bind_password else None,
            auto_bind=False,
            receive_timeout=self.default_timeout,
        )

        # Bind
        if not self._conn.bind():
            raise LDAPException(f"Failed to bind to LDAP: {self._conn.result}")

        # StartTLS if requested
        if self.use_starttls:
            if use_ssl:
                raise ValueError("Cannot use StartTLS with ldaps:// scheme")
            if not self._conn.start_tls():
                raise LDAPException(f"StartTLS failed: {self._conn.result}")

        log.info(f"Connected to LDAP server at {self.url}")

    def _reconnect(self) -> None:
        """Reconnect to LDAP server."""
        log.warning("Reconnecting to LDAP server...")
        if self._conn:
            try:
                self._conn.unbind()
            except Exception:
                pass
        self._connect()

    def _with_connection(self, func):
        """Execute function with connection, handling reconnection if needed."""
        with self._lock:
            try:
                result = func(self._conn)
                return result
            except (LDAPException, OSError, IOError) as e:
                log.warning(f"LDAP operation failed, attempting reconnect: {e}")
                try:
                    self._reconnect()
                    result = func(self._conn)
                    return result
                except Exception as reconnect_err:
                    log.error(f"Reconnection failed: {reconnect_err}")
                    raise

    def close(self) -> None:
        """Close the LDAP connection."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.unbind()
                except Exception as e:
                    log.warning(f"Error closing connection: {e}")
                finally:
                    self._conn = None

    def search(
        self,
        base_dn: str,
        filter_string: str,
        scope: SearchScope = SearchScope.SUB,
        attributes: Optional[List[str]] = None,
        size_limit: int = 0,
        types_only: bool = False,
        deref_aliases: DerefAliases = DerefAliases.NEVER,
        page_size: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Execute LDAP search.

        Args:
            base_dn: Base DN for search
            filter_string: LDAP filter
            scope: Search scope
            attributes: Attributes to retrieve (None = all)
            size_limit: Maximum entries to return
            types_only: Return only attribute types
            deref_aliases: Alias dereferencing strategy
            page_size: Paging size (0 = no paging)

        Returns:
            List of entries with DN and attributes
        """
        def do_search(conn):
            search_params = {
                'search_base': base_dn,
                'search_filter': filter_string,
                'search_scope': scope.to_ldap_scope(),
                'attributes': attributes or ['*'],
                'size_limit': size_limit,
                'types_only': types_only,
                'dereference_aliases': deref_aliases.to_ldap_deref(),
            }

            if page_size > 0:
                search_params['paged_size'] = page_size

            success = conn.search(**search_params)

            if not success:
                if isinstance(conn.result.get('description'), str) and 'noSuchObject' in conn.result.get('description', ''):
                    raise LDAPNotFoundError(f"Base DN not found: {base_dn}")
                # Empty result is OK
                return []

            entries = []
            for entry in conn.entries:
                attrs = {}
                for attr_name in entry.entry_attributes:
                    attr_val = entry[attr_name].values
                    # Convert to list of strings
                    attrs[attr_name] = [str(v) for v in attr_val]
                entries.append({
                    'dn': entry.entry_dn,
                    'attributes': attrs
                })

            return entries

        return self._with_connection(do_search)

    def get_entry(
        self,
        dn: str,
        attributes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch a single entry by DN.

        Args:
            dn: Distinguished name
            attributes: Attributes to retrieve (None = all)

        Returns:
            Entry with DN and attributes
        """
        entries = self.search(
            base_dn=dn,
            filter_string="(objectClass=*)",
            scope=SearchScope.BASE,
            attributes=attributes,
            size_limit=1,
        )

        if not entries:
            raise LDAPNotFoundError(f"Entry not found: {dn}")

        return entries[0]

    def add_entry(self, dn: str, attributes: Dict[str, List[str]]) -> None:
        """
        Create a new LDAP entry.

        Args:
            dn: Distinguished name for new entry
            attributes: Dictionary mapping attribute names to value lists
        """
        def do_add(conn):
            success = conn.add(dn, attributes=attributes)
            if not success:
                raise LDAPException(f"Failed to add entry: {conn.result}")

        self._with_connection(do_add)

    def modify_entry(
        self,
        dn: str,
        modifications: List[Dict[str, Any]],
    ) -> None:
        """
        Modify an LDAP entry.

        Args:
            dn: Distinguished name
            modifications: List of modifications, each with:
                - operation: add, replace, or delete
                - attribute: attribute name
                - values: list of values
        """
        from ldap3 import MODIFY_ADD, MODIFY_REPLACE, MODIFY_DELETE

        def do_modify(conn):
            changes = {}
            for mod in modifications:
                operation = ModifyOperation(mod['operation'].lower())
                attribute = mod['attribute'].strip()
                values = mod.get('values', [])

                if not attribute:
                    raise ValueError("Modification attribute cannot be empty")

                if operation == ModifyOperation.ADD:
                    if not values:
                        raise ValueError(f"Add operation for {attribute} requires values")
                    changes[attribute] = [(MODIFY_ADD, values)]
                elif operation == ModifyOperation.REPLACE:
                    if not values:
                        raise ValueError(f"Replace operation for {attribute} requires values")
                    changes[attribute] = [(MODIFY_REPLACE, values)]
                elif operation == ModifyOperation.DELETE:
                    changes[attribute] = [(MODIFY_DELETE, values)]
                else:
                    raise ValueError(f"Unsupported operation: {operation}")

            success = conn.modify(dn, changes)
            if not success:
                raise LDAPException(f"Failed to modify entry: {conn.result}")

        self._with_connection(do_modify)

    def delete_entry(self, dn: str) -> None:
        """
        Delete an LDAP entry.

        Args:
            dn: Distinguished name to delete
        """
        def do_delete(conn):
            success = conn.delete(dn)
            if not success:
                raise LDAPException(f"Failed to delete entry: {conn.result}")

        self._with_connection(do_delete)

    def read_root_dse(
        self,
        attributes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Read the Root DSE entry.

        Args:
            attributes: Attributes to retrieve (None = all)

        Returns:
            Root DSE entry
        """
        return self.get_entry("", attributes)


__all__ = [
    'LDAPClient',
    'LDAPNotFoundError',
    'SearchScope',
    'DerefAliases',
    'ModifyOperation',
]

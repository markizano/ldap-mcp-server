"""LDIF formatter utility for converting LDAP entries to LDIF text format.

This module implements RFC 2849 LDIF format conversion for LDAP entries.
Handles both text and binary attribute values with proper base64 encoding.
"""

import base64
from typing import Any, Dict, List


def _encode_value(value: Any) -> tuple[str, str]:
    """Encode a single attribute value for LDIF output.

    Returns (separator, encoded_value) where separator is ':' for plain text
    and '::' for base64-encoded binary or special text.

    Per RFC 2849, values must be base64-encoded if they:
    - Start with space, colon, or '<'
    - Contain non-printable characters (outside ASCII 32-126)
    - Are binary data (bytes)

    Args:
        value: Value to encode (can be bytes, string, or any type)

    Returns:
        Tuple of (separator, encoded_value) where separator is ':' or '::'
    """
    if isinstance(value, bytes):
        return '::', base64.b64encode(value).decode('ascii')

    s = str(value)

    # RFC 2849: values starting with space, colon, or <, or containing
    # non-printable chars must be base64-encoded.
    if s and (s[0] in (' ', ':', '<') or any(ord(c) > 126 or ord(c) < 32 for c in s)):
        return '::', base64.b64encode(s.encode('utf-8')).decode('ascii')

    return ':', s


def entry_to_ldif(dn: str, attributes: Dict[str, Any]) -> str:
    """Convert a single LDAP entry to an LDIF block.

    Args:
        dn: Distinguished name of the entry
        attributes: Dictionary mapping attribute names to values (list or single value)

    Returns:
        LDIF block as a string (no trailing newline)
    """
    lines = [f'dn: {dn}']

    for attr_name in sorted(attributes.keys()):
        values = attributes[attr_name]

        # Normalize to list
        if not isinstance(values, list):
            values = [values]

        # Output each value
        for value in values:
            sep, encoded = _encode_value(value)
            lines.append(f'{attr_name}{sep} {encoded}')

    return '\n'.join(lines)


def entries_to_ldif(entries: List[Dict[str, Any]]) -> str:
    """Convert a list of LDAP entries to a full LDIF document.

    Each entry dict must have 'dn' (str) and 'attributes' (dict) keys.
    Entries are separated by a blank line.

    Args:
        entries: List of entry dicts with 'dn' and 'attributes' keys

    Returns:
        Complete LDIF document as a string
    """
    if not entries:
        return ''

    blocks = [entry_to_ldif(e['dn'], e.get('attributes', {})) for e in entries]
    return '\n\n'.join(blocks)


__all__ = ['entry_to_ldif', 'entries_to_ldif']

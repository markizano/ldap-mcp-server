"""Tests for LDIF formatting utilities."""

import base64
import pytest
from ldap_mcp_server.ldif import _encode_value, entry_to_ldif, entries_to_ldif


class TestEncodeValue:
    """Tests for _encode_value helper function."""
    
    def test_plain_text(self):
        """Plain ASCII text should use : separator."""
        sep, val = _encode_value('hello')
        assert sep == ':'
        assert val == 'hello'
    
    def test_binary_data(self):
        """Binary data should be base64-encoded with :: separator."""
        binary = b'\x00\x01\x02\xff'
        sep, val = _encode_value(binary)
        assert sep == '::'
        assert val == base64.b64encode(binary).decode('ascii')
    
    def test_leading_space(self):
        """Values starting with space must be base64-encoded."""
        sep, val = _encode_value(' leading space')
        assert sep == '::'
        encoded = base64.b64decode(val).decode('utf-8')
        assert encoded == ' leading space'
    
    def test_leading_colon(self):
        """Values starting with colon must be base64-encoded."""
        sep, val = _encode_value(':colon')
        assert sep == '::'
        encoded = base64.b64decode(val).decode('utf-8')
        assert encoded == ':colon'
    
    def test_leading_angle_bracket(self):
        """Values starting with < must be base64-encoded."""
        sep, val = _encode_value('<angle>')
        assert sep == '::'
        encoded = base64.b64decode(val).decode('utf-8')
        assert encoded == '<angle>'
    
    def test_non_printable_chars(self):
        """Values with non-printable characters must be base64-encoded."""
        sep, val = _encode_value('hello\nworld')
        assert sep == '::'
        encoded = base64.b64decode(val).decode('utf-8')
        assert encoded == 'hello\nworld'
    
    def test_numeric_value(self):
        """Numeric values should be converted to string."""
        sep, val = _encode_value(12345)
        assert sep == ':'
        assert val == '12345'


class TestEntryToLdif:
    """Tests for entry_to_ldif function."""
    
    def test_single_valued_attributes(self):
        """Single-valued attributes should be formatted correctly."""
        dn = 'uid=jsmith,ou=users,dc=example,dc=com'
        attrs = {
            'uid': ['jsmith'],
            'cn': ['John Smith'],
            'sn': ['Smith'],
        }
        result = entry_to_ldif(dn, attrs)
        
        assert 'dn: uid=jsmith,ou=users,dc=example,dc=com' in result
        assert 'cn: John Smith' in result
        assert 'sn: Smith' in result
        assert 'uid: jsmith' in result
    
    def test_multi_valued_attributes(self):
        """Multi-valued attributes should each get a line."""
        dn = 'uid=jsmith,ou=users,dc=example,dc=com'
        attrs = {
            'objectClass': ['inetOrgPerson', 'organizationalPerson', 'person'],
        }
        result = entry_to_ldif(dn, attrs)
        
        assert result.count('objectClass:') == 3
        assert 'objectClass: inetOrgPerson' in result
        assert 'objectClass: organizationalPerson' in result
        assert 'objectClass: person' in result
    
    def test_sorted_attributes(self):
        """Attributes should be sorted alphabetically."""
        dn = 'uid=test,dc=example,dc=com'
        attrs = {
            'zulu': ['last'],
            'alpha': ['first'],
            'bravo': ['second'],
        }
        result = entry_to_ldif(dn, attrs)
        lines = result.split('\n')
        
        # Skip DN line, check attribute order
        attr_lines = [l for l in lines[1:] if l]
        assert attr_lines[0].startswith('alpha:')
        assert attr_lines[1].startswith('bravo:')
        assert attr_lines[2].startswith('zulu:')
    
    def test_non_list_values(self):
        """Non-list values should be normalized to lists."""
        dn = 'uid=test,dc=example,dc=com'
        attrs = {
            'singleValue': 'not_a_list',
        }
        result = entry_to_ldif(dn, attrs)
        assert 'singleValue: not_a_list' in result
    
    def test_empty_attributes(self):
        """Entry with no attributes should only have DN."""
        dn = 'dc=example,dc=com'
        attrs = {}
        result = entry_to_ldif(dn, attrs)
        assert result == 'dn: dc=example,dc=com'
    
    def test_binary_attribute_value(self):
        """Binary attribute values should be base64-encoded."""
        dn = 'cn=cert,dc=example,dc=com'
        binary_data = b'\x00\x01\x02\xff'
        attrs = {
            'certificateData': [binary_data],
        }
        result = entry_to_ldif(dn, attrs)
        
        assert 'certificateData::' in result
        encoded = base64.b64encode(binary_data).decode('ascii')
        assert f'certificateData:: {encoded}' in result


class TestEntriesToLdif:
    """Tests for entries_to_ldif function."""
    
    def test_empty_list(self):
        """Empty entry list should return empty string."""
        result = entries_to_ldif([])
        assert result == ''
    
    def test_single_entry(self):
        """Single entry should be formatted without trailing newlines."""
        entries = [{
            'dn': 'uid=jsmith,dc=example,dc=com',
            'attributes': {'cn': ['John Smith']}
        }]
        result = entries_to_ldif(entries)
        
        assert 'dn: uid=jsmith,dc=example,dc=com' in result
        assert 'cn: John Smith' in result
        assert not result.endswith('\n\n')
    
    def test_multiple_entries(self):
        """Multiple entries should be separated by blank line."""
        entries = [
            {
                'dn': 'uid=jsmith,dc=example,dc=com',
                'attributes': {'cn': ['John Smith']}
            },
            {
                'dn': 'uid=bjones,dc=example,dc=com',
                'attributes': {'cn': ['Betty Jones']}
            }
        ]
        result = entries_to_ldif(entries)
        
        # Should have two blocks separated by blank line
        blocks = result.split('\n\n')
        assert len(blocks) == 2
        assert 'dn: uid=jsmith,dc=example,dc=com' in blocks[0]
        assert 'dn: uid=bjones,dc=example,dc=com' in blocks[1]
    
    def test_entry_without_attributes_key(self):
        """Entry without 'attributes' key should be handled gracefully."""
        entries = [
            {'dn': 'dc=example,dc=com'}
        ]
        result = entries_to_ldif(entries)
        assert result == 'dn: dc=example,dc=com'
    
    def test_full_example(self):
        """Full realistic example with multiple entries and attributes."""
        entries = [
            {
                'dn': 'uid=jsmith,ou=users,dc=example,dc=com',
                'attributes': {
                    'objectClass': ['inetOrgPerson', 'organizationalPerson'],
                    'uid': ['jsmith'],
                    'cn': ['John Smith'],
                    'sn': ['Smith'],
                    'mail': ['jsmith@example.com'],
                }
            },
            {
                'dn': 'uid=bjones,ou=users,dc=example,dc=com',
                'attributes': {
                    'objectClass': ['inetOrgPerson'],
                    'uid': ['bjones'],
                    'cn': ['Betty Jones'],
                    'sn': ['Jones'],
                }
            }
        ]
        result = entries_to_ldif(entries)
        
        # Verify structure
        assert result.count('dn:') == 2
        assert '\n\n' in result  # Blank line separator
        
        # Verify first entry
        assert 'uid=jsmith,ou=users,dc=example,dc=com' in result
        assert 'mail: jsmith@example.com' in result
        
        # Verify second entry
        assert 'uid=bjones,ou=users,dc=example,dc=com' in result
        assert 'cn: Betty Jones' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

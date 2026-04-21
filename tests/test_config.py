"""Tests for configuration management."""

import os
import pytest
from ldap_mcp_server.config import Config
from ldap_mcp_server.cli import parse_args


class TestConfig:
    """Tests for Config dataclass."""
    
    def test_defaults(self):
        """Test default configuration values."""
        cfg = Config()
        
        assert cfg.transport == 'sse'
        assert cfg.host == '0.0.0.0'
        assert cfg.port == 9090
        assert cfg.url == 'ldap://localhost:389'
        assert cfg.bind_dn == ''
        assert cfg.bind_password == ''
        assert cfg.use_starttls is False
        assert cfg.insecure_tls is False
        assert cfg.read_write is False
        assert cfg.timeout == 30
        assert cfg.log_level == 'INFO'
        assert cfg.api_key is None
    
    def test_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv('MCP_HOST', '127.0.0.1')
        monkeypatch.setenv('MCP_PORT', '8080')
        monkeypatch.setenv('LDAP_URI', 'ldaps://ldap.example.com:636')
        monkeypatch.setenv('LDAP_BIND_DN', 'cn=admin,dc=test,dc=com')
        monkeypatch.setenv('LDAP_BIND_PASSWORD', 'secret')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('LDAP_MCP_SERVER_API_KEY', 'mykey123')
        
        cfg = Config.from_env()
        
        assert cfg.host == '127.0.0.1'
        assert cfg.port == 8080
        assert cfg.url == 'ldaps://ldap.example.com:636'
        assert cfg.bind_dn == 'cn=admin,dc=test,dc=com'
        assert cfg.bind_password == 'secret'
        assert cfg.log_level == 'DEBUG'
        assert cfg.api_key == 'mykey123'
    
    def test_validate_valid_config(self):
        """Valid configuration should pass validation."""
        cfg = Config(
            transport='sse',
            port=9090,
            url='ldap://localhost:389',
            timeout=30,
            log_level='INFO'
        )
        cfg.validate()  # Should not raise
    
    def test_validate_invalid_transport(self):
        """Invalid transport should fail validation."""
        cfg = Config(transport='invalid')
        with pytest.raises(ValueError, match='Invalid transport'):
            cfg.validate()
    
    def test_validate_invalid_port_too_low(self):
        """Port below 1 should fail validation."""
        cfg = Config(port=0)
        with pytest.raises(ValueError, match='Invalid port'):
            cfg.validate()
    
    def test_validate_invalid_port_too_high(self):
        """Port above 65535 should fail validation."""
        cfg = Config(port=65536)
        with pytest.raises(ValueError, match='Invalid port'):
            cfg.validate()
    
    def test_validate_invalid_timeout(self):
        """Non-positive timeout should fail validation."""
        cfg = Config(timeout=0)
        with pytest.raises(ValueError, match='Invalid timeout'):
            cfg.validate()
    
    def test_validate_missing_ldap_uri(self):
        """Empty LDAP_URI should fail validation."""
        cfg = Config(url='')
        with pytest.raises(ValueError, match='LDAP_URI is required'):
            cfg.validate()
    
    def test_validate_invalid_log_level(self):
        """Invalid log level should fail validation."""
        cfg = Config(log_level='INVALID')
        with pytest.raises(ValueError, match='Invalid log level'):
            cfg.validate()


class TestCLIParsing:
    """Tests for CLI argument parsing."""
    
    def test_parse_default_args(self, monkeypatch):
        """Parsing with no args should use environment defaults."""
        # Clear relevant env vars
        for key in ['MCP_HOST', 'MCP_PORT', 'LDAP_URI', 'LDAP_BIND_DN', 
                    'LDAP_BIND_PASSWORD', 'LOG_LEVEL', 'LDAP_MCP_SERVER_API_KEY']:
            monkeypatch.delenv(key, raising=False)
        
        cfg = parse_args([])
        
        assert cfg.transport == 'sse'
        assert cfg.host == '0.0.0.0'
        assert cfg.port == 9090
        assert cfg.url == 'ldap://localhost:389'
        assert cfg.read_write is False
    
    def test_parse_transport_flag(self, monkeypatch):
        """--transport flag should override default."""
        for key in ['MCP_HOST', 'MCP_PORT', 'LDAP_URI']:
            monkeypatch.delenv(key, raising=False)
        
        cfg = parse_args(['--transport', 'stdio'])
        assert cfg.transport == 'stdio'
    
    def test_parse_host_and_port(self, monkeypatch):
        """--host and --port flags should override defaults."""
        for key in ['MCP_HOST', 'MCP_PORT', 'LDAP_URI']:
            monkeypatch.delenv(key, raising=False)
        
        cfg = parse_args(['--host', '192.168.1.100', '--port', '8888'])
        assert cfg.host == '192.168.1.100'
        assert cfg.port == 8888
    
    def test_parse_ldap_url(self, monkeypatch):
        """--url flag should override default LDAP URL."""
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args(['--url', 'ldaps://secure.ldap.com:636'])
        assert cfg.url == 'ldaps://secure.ldap.com:636'
    
    def test_parse_bind_credentials(self, monkeypatch):
        """--bind-dn and --bind-password flags should work."""
        for key in ['LDAP_URI', 'LDAP_BIND_DN', 'LDAP_BIND_PASSWORD']:
            monkeypatch.delenv(key, raising=False)
        
        cfg = parse_args([
            '--bind-dn', 'cn=service,dc=example,dc=com',
            '--bind-password', 'secret123'
        ])
        assert cfg.bind_dn == 'cn=service,dc=example,dc=com'
        assert cfg.bind_password == 'secret123'
    
    def test_parse_starttls_flag(self, monkeypatch):
        """--starttls flag should enable StartTLS."""
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args(['--starttls'])
        assert cfg.use_starttls is True
    
    def test_parse_insecure_flag(self, monkeypatch):
        """--insecure flag should disable TLS verification."""
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args(['--insecure'])
        assert cfg.insecure_tls is True
    
    def test_parse_read_write_flag(self, monkeypatch):
        """--read-write flag should enable write operations."""
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args(['--read-write'])
        assert cfg.read_write is True
    
    def test_parse_timeout_flag(self, monkeypatch):
        """--timeout flag should set LDAP timeout."""
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args(['--timeout', '60'])
        assert cfg.timeout == 60
    
    def test_parse_log_level_flag(self, monkeypatch):
        """--log-level flag should set logging level."""
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args(['--log-level', 'DEBUG'])
        assert cfg.log_level == 'DEBUG'
    
    def test_cli_overrides_env(self, monkeypatch):
        """CLI flags should take precedence over environment variables."""
        monkeypatch.setenv('MCP_PORT', '9999')
        monkeypatch.setenv('LDAP_URI', 'ldap://env.example.com')
        
        cfg = parse_args(['--port', '7777', '--url', 'ldap://cli.example.com'])
        
        # CLI flags should win
        assert cfg.port == 7777
        assert cfg.url == 'ldap://cli.example.com'
    
    def test_api_key_from_env_only(self, monkeypatch):
        """API key should only come from environment, not CLI."""
        monkeypatch.setenv('LDAP_MCP_SERVER_API_KEY', 'env-key')
        monkeypatch.delenv('LDAP_URI', raising=False)
        
        cfg = parse_args([])
        assert cfg.api_key == 'env-key'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

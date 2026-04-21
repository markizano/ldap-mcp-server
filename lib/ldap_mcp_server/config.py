"""Configuration management for LDAP MCP Server.

This module handles configuration from environment variables and CLI flags.
CLI flags take precedence over environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration for LDAP MCP Server."""

    # Transport
    transport: str = 'sse'

    # Server binding (SSE mode only)
    host: str = '0.0.0.0'
    port: int = 9090

    # LDAP connection
    url: str = 'ldap://localhost:389'
    bind_dn: str = ''
    bind_password: str = ''

    # TLS options
    use_starttls: bool = False
    insecure_tls: bool = False

    # Operation mode
    read_write: bool = False

    # Timeouts
    timeout: int = 30

    # Logging
    log_level: str = 'INFO'

    # Authentication (SSE mode only)
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv('MCP_HOST', '0.0.0.0'),
            port=int(os.getenv('MCP_PORT', '9090')),
            url=os.getenv('LDAP_URI', 'ldap://localhost:389'),
            bind_dn=os.getenv('LDAP_BIND_DN', ''),
            bind_password=os.getenv('LDAP_BIND_PASSWORD', ''),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            api_key=os.getenv('LDAP_MCP_SERVER_API_KEY'),
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if self.transport not in ('stdio', 'sse'):
            raise ValueError(f'Invalid transport: {self.transport} (must be stdio or sse)')

        if self.port < 1 or self.port > 65535:
            raise ValueError(f'Invalid port: {self.port} (must be 1-65535)')

        if self.timeout < 1:
            raise ValueError(f'Invalid timeout: {self.timeout} (must be positive)')

        if not self.url:
            raise ValueError('LDAP_URI is required')

        valid_log_levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f'Invalid log level: {self.log_level} (must be one of {valid_log_levels})')


__all__ = ['Config']

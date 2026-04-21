"""ASGI middleware for API key authentication.

This middleware enforces Bearer token or X-API-Key header authentication
for all requests except whitelisted paths.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that enforces API key authentication."""

    SKIP_PATHS = {'/', '/health'}

    def __init__(self, app, api_key: str):
        """Initialize middleware.

        Args:
            app: ASGI application to wrap
            api_key: Expected API key for authentication
        """
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        """Process request and enforce authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next ASGI handler in the chain

        Returns:
            HTTP response (401 if unauthorized, or result from next handler)
        """
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        token = ''
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif auth_header:
            token = auth_header

        if not token:
            token = request.headers.get('X-API-Key', '')

        if token != self.api_key:
            log.warning('Unauthorized access attempt from %s', request.client.host if request.client else 'unknown')
            return JSONResponse(
                {'error': 'Unauthorized — invalid or missing API key'},
                status_code=401,
                headers={'WWW-Authenticate': 'Bearer'},
            )

        return await call_next(request)


__all__ = ['APIKeyMiddleware']

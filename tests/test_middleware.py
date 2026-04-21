"""Tests for API key authentication middleware."""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from ldap_mcp_server.middleware import APIKeyMiddleware


async def root(request):
    """Root endpoint."""
    return PlainTextResponse('root')


async def health(request):
    """Health check endpoint."""
    return PlainTextResponse('ok')


async def protected(request):
    """Protected endpoint."""
    return PlainTextResponse('secret data')


@pytest.fixture
def test_app():
    """Create a test Starlette app with API key middleware."""
    routes = [
        Route('/', root),
        Route('/health', health),
        Route('/protected', protected),
    ]
    
    app = Starlette(routes=routes)
    
    # Wrap with middleware (direct instantiation, not add_middleware)
    app = APIKeyMiddleware(app, api_key='testkey123')
    
    return app


class TestAPIKeyMiddleware:
    """Tests for APIKeyMiddleware class."""
    
    def test_root_path_bypasses_auth(self, test_app):
        """Root path (/) should bypass authentication."""
        client = TestClient(test_app)
        response = client.get('/')
        
        assert response.status_code == 200
        assert response.text == 'root'
    
    def test_health_path_bypasses_auth(self, test_app):
        """Health check path (/health) should bypass authentication."""
        client = TestClient(test_app)
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.text == 'ok'
    
    def test_protected_route_requires_auth(self, test_app):
        """Protected routes should require authentication."""
        client = TestClient(test_app)
        response = client.get('/protected')
        
        assert response.status_code == 401
        assert 'Unauthorized' in response.json()['error']
    
    def test_valid_bearer_token(self, test_app):
        """Valid Bearer token should grant access."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'Authorization': 'Bearer testkey123'}
        )
        
        assert response.status_code == 200
        assert response.text == 'secret data'
    
    def test_invalid_bearer_token(self, test_app):
        """Invalid Bearer token should be rejected."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'Authorization': 'Bearer wrongkey'}
        )
        
        assert response.status_code == 401
        assert 'Unauthorized' in response.json()['error']
    
    def test_valid_x_api_key_header(self, test_app):
        """Valid X-API-Key header should grant access."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'X-API-Key': 'testkey123'}
        )
        
        assert response.status_code == 200
        assert response.text == 'secret data'
    
    def test_invalid_x_api_key_header(self, test_app):
        """Invalid X-API-Key header should be rejected."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'X-API-Key': 'wrongkey'}
        )
        
        assert response.status_code == 401
    
    def test_plain_authorization_header(self, test_app):
        """Authorization header without Bearer prefix should work."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'Authorization': 'testkey123'}
        )
        
        assert response.status_code == 200
        assert response.text == 'secret data'
    
    def test_missing_auth_header(self, test_app):
        """Request without auth header should be rejected."""
        client = TestClient(test_app)
        response = client.get('/protected')
        
        assert response.status_code == 401
        assert response.headers['WWW-Authenticate'] == 'Bearer'
    
    def test_empty_bearer_token(self, test_app):
        """Empty Bearer token should be rejected."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'Authorization': 'Bearer '}
        )
        
        assert response.status_code == 401
    
    def test_case_sensitive_api_key(self, test_app):
        """API key comparison should be case-sensitive."""
        client = TestClient(test_app)
        response = client.get(
            '/protected',
            headers={'Authorization': 'Bearer TESTKEY123'}  # Wrong case
        )
        
        assert response.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

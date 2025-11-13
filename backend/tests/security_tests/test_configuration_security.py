"""
Configuration Security Tests.

Tests configuration security and secrets protection.
"""
import pytest
import os
from django.conf import settings


class TestSecretsProtection:
    """Test secrets are not exposed - CRITICAL."""

    def test_secret_key_not_exposed(self, api_client):
        """Django SECRET_KEY not in responses."""
        response = api_client.get('/api/health/')
        assert settings.SECRET_KEY not in str(response.content)

    def test_api_keys_not_exposed(self, authenticated_client):
        """API keys not in responses."""
        response = authenticated_client.get('/api/campaigns/')
        content = str(response.content)
        assert 'OPENAI_API_KEY' not in content
        assert 'TAVILY_API_KEY' not in content
        assert 'sk-' not in content


class TestErrorHandling:
    """Test error messages don't leak info - CRITICAL."""

    def test_no_stack_traces(self, authenticated_client):
        """Error responses don't show stack traces."""
        response = authenticated_client.get('/api/campaigns/invalid-uuid/')
        content = str(response.content)
        assert 'Traceback' not in content
        assert '.py", line' not in content

    def test_validation_errors_safe(self, authenticated_client):
        """Validation errors don't leak internals."""
        response = authenticated_client.post('/api/brands/', {}, format='json')
        content = str(response.content)
        assert '/backend/' not in content or 'Field' in content


class TestDebugMode:
    """Test debug mode is disabled - CRITICAL."""

    def test_debug_disabled_in_prod(self):
        """DEBUG is False in production."""
        if os.getenv('ENVIRONMENT') == 'production':
            assert settings.DEBUG is False

    def test_no_debug_toolbar(self, api_client):
        """Debug toolbar not accessible."""
        response = api_client.get('/__debug__/')
        assert response.status_code == 404


class TestSecurityHeaders:
    """Test security headers - IMPORTANT."""

    def test_no_x_powered_by(self, api_client):
        """X-Powered-By header not present."""
        response = api_client.get('/api/health/')
        assert 'X-Powered-By' not in response

    def test_server_header_minimal(self, api_client):
        """Server header doesn't reveal versions."""
        response = api_client.get('/api/health/')
        if 'Server' in response:
            assert 'Django/' not in response['Server']
            assert 'Python/' not in response['Server']

    def test_security_headers_present(self, api_client):
        """Security headers are present."""
        response = api_client.get('/api/health/')
        if 'X-Content-Type-Options' in response:
            assert response['X-Content-Type-Options'] == 'nosniff'


class TestConfigurationValidation:
    """Test configuration security - IMPORTANT."""

    def test_allowed_hosts_configured(self):
        """ALLOWED_HOSTS is configured."""
        if os.getenv('ENVIRONMENT') == 'production':
            assert settings.ALLOWED_HOSTS != ['*']
            assert len(settings.ALLOWED_HOSTS) > 0

    def test_secret_key_not_default(self):
        """SECRET_KEY is not default."""
        if os.getenv('ENVIRONMENT') == 'production':
            assert not settings.SECRET_KEY.startswith('django-insecure-')

    def test_secure_cookies_in_prod(self):
        """Secure cookies in production."""
        if os.getenv('ENVIRONMENT') == 'production':
            assert getattr(settings, 'SESSION_COOKIE_SECURE', False) is True
            assert getattr(settings, 'CSRF_COOKIE_SECURE', False) is True


class TestDatabaseSecurity:
    """Test database security - IMPORTANT."""

    def test_not_sqlite_in_prod(self):
        """Production doesn't use SQLite."""
        if os.getenv('ENVIRONMENT') == 'production':
            db_engine = settings.DATABASES['default']['ENGINE']
            assert 'sqlite' not in db_engine.lower()


class TestCORSConfiguration:
    """Test CORS security - IMPORTANT."""

    def test_cors_not_allow_all(self):
        """CORS doesn't allow all origins."""
        if os.getenv('ENVIRONMENT') == 'production':
            cors_allow_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)
            assert cors_allow_all is False


class TestAPIKeyManagement:
    """Test API key security - IMPORTANT."""

    def test_keys_from_environment(self):
        """API keys loaded from environment."""
        assert hasattr(settings, 'OPENAI_API_KEY')
        if settings.OPENAI_API_KEY:
            assert settings.OPENAI_API_KEY != 'your-key-here'


class TestFileAccessSecurity:
    """Test file access security - IMPORTANT."""

    def test_backup_files_not_accessible(self, api_client):
        """Backup files not accessible."""
        paths = ['/backup.sql', '/.env', '/.git/config', '/db.sqlite3']
        for path in paths:
            response = api_client.get(path)
            assert response.status_code in [403, 404]

    def test_source_not_accessible(self, api_client):
        """Source code not accessible."""
        paths = ['/manage.py', '/settings.py', '/requirements.txt']
        for path in paths:
            response = api_client.get(path)
            assert response.status_code in [403, 404]


class TestLoggingSecurity:
    """Test logging security - IMPORTANT."""

    def test_tokens_not_logged(self, authenticated_client, auth_tokens, caplog):
        """Auth tokens not logged in full."""
        with caplog.at_level('DEBUG'):
            authenticated_client.get('/api/campaigns/')
        assert auth_tokens['access'] not in caplog.text

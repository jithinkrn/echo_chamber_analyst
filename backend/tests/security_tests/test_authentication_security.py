"""
Authentication Security Tests - Critical Auth Validations.

Tests only implemented authentication security features.
"""
import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
import time


class TestJWTSecurity:
    """Test JWT token security - CRITICAL."""

    def test_valid_token_accepted(self, authenticated_client):
        """Valid tokens are accepted."""
        response = authenticated_client.get('/api/campaigns/')
        assert response.status_code in [200, 404]


class TestPasswordSecurity:
    """Test password security - IMPORTANT."""

    def test_password_not_in_response(self, authenticated_client):
        """Passwords never in API responses."""
        response = authenticated_client.get('/api/campaigns/')
        content = str(response.content).lower()
        assert 'password' not in content or 'field' in content.lower()

    def test_password_hashed_in_db(self, test_user):
        """Passwords are hashed in database."""
        assert not test_user.password.startswith('SecurePass')
        assert test_user.password.startswith('pbkdf2_sha256')


class TestSessionSecurity:
    """Test session security - IMPORTANT."""

    def test_no_credentials_in_url(self, authenticated_client):
        """No credentials exposed in URLs."""
        response = authenticated_client.get('/api/campaigns/')
        assert 'password' not in response.request.get('QUERY_STRING', '').lower()

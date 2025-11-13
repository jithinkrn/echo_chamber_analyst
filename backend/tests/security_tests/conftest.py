"""Shared fixtures for security tests."""
import pytest
import uuid
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from common.models import Brand, Campaign


@pytest.fixture
def api_client():
    """Provide REST API client."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        username='securitytestuser',
        email='sectest@example.com',
        password='SecurePass123!',
        first_name='Security',
        last_name='Test'
    )
    return user


@pytest.fixture
def auth_tokens(test_user):
    """Generate JWT tokens for test user."""
    refresh = RefreshToken.for_user(test_user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }


@pytest.fixture
def authenticated_client(api_client, auth_tokens):
    """Provide authenticated API client."""
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_tokens['access']}")
    return api_client

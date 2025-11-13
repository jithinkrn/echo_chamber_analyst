"""
API Security Tests - Critical API Security.

Tests API security for implemented endpoints.
"""
import pytest


class TestInputValidation:
    """Test input validation - CRITICAL."""

    def test_invalid_uuid_rejected(self, authenticated_client):
        """Invalid UUIDs are rejected."""
        response = authenticated_client.get('/api/campaigns/not-a-uuid/')
        assert response.status_code in [400, 404]

"""
Injection Security Tests - Critical Injection Prevention.

Tests injection attack prevention for implemented features.
"""
import pytest


class TestSQLInjectionPrevention:
    """Test SQL injection prevention - CRITICAL."""

    def test_filter_injection_safe(self, authenticated_client):
        """Query filters handle injection safely."""
        malicious = "'; DROP TABLE brands; --"
        response = authenticated_client.get(f'/api/brands/?search={malicious}')
        # Should return safe error or empty results, not 500
        assert response.status_code in [200, 400, 404]

    def test_order_injection_safe(self, authenticated_client):
        """Order parameters handle injection safely."""
        malicious = "name; DROP TABLE--"
        response = authenticated_client.get(f'/api/campaigns/?ordering={malicious}')
        assert response.status_code in [200, 400, 404]


class TestXSSPrevention:
    """Test XSS prevention - CRITICAL."""

    def test_html_in_input_sanitized(self, authenticated_client):
        """HTML in input is sanitized."""
        xss_payload = "<script>alert('XSS')</script>"
        response = authenticated_client.post('/api/brands/', {
            'name': xss_payload,
            'description': 'Test brand'
        }, format='json')

        if response.status_code == 201:
            # If created, verify it's sanitized
            content = str(response.content)
            assert '<script>' not in content or '&lt;script&gt;' in content

    def test_javascript_in_input_sanitized(self, authenticated_client):
        """JavaScript in input is sanitized."""
        js_payload = "javascript:alert('XSS')"
        response = authenticated_client.post('/api/brands/', {
            'name': 'Test',
            'description': js_payload
        }, format='json')

        if response.status_code == 201:
            content = str(response.content)
            assert 'javascript:' not in content or 'invalid' in content.lower()


class TestCommandInjectionPrevention:
    """Test command injection prevention - CRITICAL."""

    def test_special_chars_in_filenames(self, authenticated_client):
        """Special characters in filenames handled safely."""
        dangerous_chars = "; rm -rf / #"
        response = authenticated_client.get(f'/api/campaigns/?name={dangerous_chars}')
        # Should handle gracefully, not execute commands
        assert response.status_code in [200, 400, 404]


class TestPathTraversalPrevention:
    """Test path traversal prevention - CRITICAL."""

    def test_dot_dot_slash_blocked(self, api_client):
        """Path traversal with ../ blocked."""
        paths = ['../../etc/passwd', '../../../settings.py', '....//....//etc/passwd']
        for path in paths:
            response = api_client.get(f'/api/brands/{path}')
            assert response.status_code in [400, 404]

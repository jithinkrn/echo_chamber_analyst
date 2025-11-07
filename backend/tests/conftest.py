"""
Pytest configuration for Django tests.
"""
import os
import django
from django.conf import settings

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()


def pytest_configure(config):
    """Configure pytest for Django."""
    # Ensure Django is set up
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'common',
                'api',
                'authentication',
            ],
            SECRET_KEY='test-secret-key-for-testing-only',
        )
        django.setup()

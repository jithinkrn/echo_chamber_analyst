"""
Pytest configuration for integration tests.

Integration tests use real database, Redis, and Celery workers.
"""
import pytest
import os
from datetime import datetime, timedelta
from django.test import TransactionTestCase
from django.db import connection

# Import results recording plugin
pytest_plugins = ['tests.integration_test.conftest_results']


# Mark all tests in this directory as integration tests
def pytest_collection_modifyitems(items):
    for item in items:
        if "integration_test" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope='function')
def db():
    """Simple db fixture that ensures Django is ready."""
    # Django is already setup via __init__.py
    # Just yield to allow test to run
    yield
    # Cleanup happens automatically with Django's test database


@pytest.fixture(scope='function')
def test_user(db):
    """Create a test user for campaigns."""
    from django.contrib.auth.models import User
    import uuid
    username = f'test_user_{uuid.uuid4().hex[:8]}'
    user = User.objects.create_user(
        username=username,
        email=f'{username}@integration.com',
        password='testpass123'
    )
    yield user
    # Cleanup
    user.delete()


@pytest.fixture(scope='function')
def test_brand(db):
    """Create a test brand."""
    from common.models import Brand
    import uuid
    brand = Brand.objects.create(
        name=f'Test Brand {uuid.uuid4().hex[:8]}',
        description='Integration test brand',
        industry='Technology',
        primary_keywords=['test', 'integration'],
        sources=['reddit']
    )
    yield brand
    # Cleanup
    brand.delete()


@pytest.fixture(scope='function')
def test_campaign_automatic(db, test_user, test_brand):
    """Create a test automatic (Brand Analytics) campaign."""
    from common.models import Campaign
    campaign = Campaign.objects.create(
        name=f'Integration Test Campaign Auto {datetime.now().timestamp()}',
        description='Automatic Brand Analytics test campaign',
        brand=test_brand,
        owner=test_user,
        campaign_type='automatic',
        status='active',
        keywords=['Nike', 'Air Jordan', 'sneakers'],
        sources=['reddit'],
        collection_months=3,  # Collect 3 months of data
        budget_limit=50.00
    )
    return campaign


@pytest.fixture(scope='function')
def test_campaign_custom(db, test_user):
    """Create a test custom campaign."""
    from common.models import Campaign
    campaign = Campaign.objects.create(
        name=f'Integration Test Campaign Custom {datetime.now().timestamp()}',
        description='Custom campaign test',
        owner=test_user,
        campaign_type='custom',
        status='active',
        keywords=['sustainability', 'eco-friendly'],
        sources=['reddit'],
        collection_months=3,
        budget_limit=30.00,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30)
    )
    return campaign


@pytest.fixture(scope='function')
def cleanup_test_data(db):
    """Cleanup test data after test runs."""
    yield
    # Cleanup is handled by Django test database isolation
    # But you can add explicit cleanup here if needed

"""
Pytest configuration for SHAP explainability tests.

This tests REAL LLM insight generation using SHAP explainability.
"""

import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set Django settings - pytest-django will handle the setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


@pytest.fixture(scope='function')
def sample_brand_with_data(db):
    """
    Create a REAL Brand with sample data for SHAP testing.

    Returns:
        Tuple of (brand, kpis, communities, pain_points)
    """
    # Import models inside the fixture to avoid initialization issues
    from common.models import Brand, User

    print("\n🔧 [FIXTURE] Setting up sample_brand_with_data fixture...")

    # Create test user
    print("   📝 Creating test user...")
    user = User.objects.create_user(
        username='shap_test_user',
        email='shap@test.com',
        password='testpass123'
    )
    print(f"   ✅ User created: {user.username}")

    # Create REAL Brand
    print("   📝 Creating test brand...")
    brand = Brand.objects.create(
        name='SHAP Test Brand',
        industry='Technology'
    )
    print(f"   ✅ Brand created: {brand.name} (ID: {brand.id})")

    # Sample KPIs (matching dashboard structure)
    kpis = {
        'avg_sentiment': -0.35,
        'avg_echo_score': 72.5,
        'total_mentions': 1250,
        'top_pain_point': 'Delivery delays',
        'engagement_rate': 45.3,
        'community_count': 8
    }

    # Sample communities data
    communities = [
        {
            'community_name': 'r/TechReviews',
            'platform': 'Reddit',
            'echo_score': 85.2,
            'sentiment_score': -0.42,
            'member_count': 5000,
            'post_count': 150
        },
        {
            'community_name': 'ProductForum',
            'platform': 'Reddit',
            'echo_score': 68.5,
            'sentiment_score': -0.28,
            'member_count': 3200,
            'post_count': 95
        },
        {
            'community_name': 'r/CustomerSupport',
            'platform': 'Reddit',
            'echo_score': 92.1,
            'sentiment_score': -0.65,
            'member_count': 8500,
            'post_count': 280
        }
    ]

    # Sample pain points data
    pain_points = [
        {
            'keyword': 'Delivery delays',
            'mention_count': 245,
            'sentiment_score': -0.72,
            'growth_percentage': 35.2
        },
        {
            'keyword': 'Poor customer service',
            'mention_count': 189,
            'sentiment_score': -0.68,
            'growth_percentage': 22.8
        },
        {
            'keyword': 'Quality issues',
            'mention_count': 156,
            'sentiment_score': -0.55,
            'growth_percentage': 15.4
        },
        {
            'keyword': 'High prices',
            'mention_count': 134,
            'sentiment_score': -0.48,
            'growth_percentage': 8.2
        },
        {
            'keyword': 'Shipping costs',
            'mention_count': 98,
            'sentiment_score': -0.52,
            'growth_percentage': 12.1
        }
    ]

    print("   ✅ Fixture setup complete - yielding data to test")
    yield brand, kpis, communities, pain_points

    # Cleanup
    print("\n🧹 [FIXTURE] Cleaning up test data...")
    brand.delete()
    user.delete()
    print("   ✅ Cleanup complete")


# Pytest plugin to capture and save results
class SHAPResultsPlugin:
    """Plugin to capture SHAP test results."""

    def __init__(self):
        from datetime import datetime
        self.results = {
            "test_suite": "SHAP Explainability Tests",
            "timestamp": datetime.now().isoformat(),
            "tests_run": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }

    def pytest_runtest_logreport(self, report):
        """Capture test results."""
        if report.when == 'call':
            test_info = {
                "name": report.nodeid,
                "outcome": report.outcome,
                "duration": report.duration
            }

            if report.outcome == 'failed':
                test_info['error'] = str(report.longrepr)

            self.results['tests_run'].append(test_info)
            self.results['summary']['total'] += 1

            if report.outcome == 'passed':
                self.results['summary']['passed'] += 1
            elif report.outcome == 'failed':
                self.results['summary']['failed'] += 1

    def pytest_sessionfinish(self, session, exitstatus):
        """Save results to JSON files."""
        import json
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)

        # Save overall results
        overall_file = os.path.join(results_dir, 'shap_test_results.json')
        with open(overall_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📊 SHAP test results saved to: {results_dir}/")
        print(f"   - Overall: {self.results['summary']['passed']}/{self.results['summary']['total']} passed")


def pytest_configure(config):
    """Register the results plugin."""
    plugin = SHAPResultsPlugin()
    config.pluginmanager.register(plugin, "shap_results")

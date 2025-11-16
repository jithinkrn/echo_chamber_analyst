"""
Pytest configuration for LIME explainability tests.

This tests REAL LLM text analysis using LIME explainability.
"""

import pytest
import os
import sys
import django

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from common.models import Brand, User


@pytest.fixture(scope='function')
def sample_brand_for_lime(db):
    """
    Create a REAL Brand with sample data for LIME testing.

    Returns:
        Tuple of (brand, kpis, communities)
    """
    # Create test user
    user = User.objects.create_user(
        username='lime_test_user',
        email='lime@test.com',
        password='testpass123'
    )

    # Create REAL Brand
    brand = Brand.objects.create(
        name='LIME Test Brand',
        industry='E-commerce'
    )

    # Sample KPIs
    kpis = {
        'avg_sentiment': -0.45,
        'avg_echo_score': 75.0,
        'total_mentions': 850,
        'top_pain_point': 'Shipping delays',
        'engagement_rate': 38.5,
        'community_count': 5
    }

    # Sample communities
    communities = [
        {
            'community_name': 'r/CustomerService',
            'platform': 'Reddit',
            'echo_score': 88.3,
            'sentiment_score': -0.58,
            'member_count': 12000,
            'post_count': 320
        },
        {
            'community_name': 'r/ProductReviews',
            'platform': 'Reddit',
            'echo_score': 65.2,
            'sentiment_score': -0.32,
            'member_count': 8500,
            'post_count': 185
        }
    ]

    yield brand, kpis, communities

    # Cleanup
    brand.delete()
    user.delete()


# Global storage for detailed LIME explanations
_lime_explanations = []


def store_lime_explanation(test_name, text, word_importances, prediction_proba=None):
    """
    Store LIME explanation for later saving to JSON.

    Args:
        test_name: Name of the test
        text: The text that was explained
        word_importances: List of (word, importance) tuples from LIME
        prediction_proba: Optional prediction probabilities
    """
    _lime_explanations.append({
        "test_name": test_name,
        "text": text,
        "word_importances": [
            {"word": word, "importance": float(importance)}
            for word, importance in word_importances
        ],
        "prediction_proba": prediction_proba
    })


# Pytest plugin to capture and save results
class LIMEResultsPlugin:
    """Plugin to capture LIME test results."""

    def __init__(self):
        from datetime import datetime
        self.results = {
            "test_suite": "LIME Sentiment Explainability Tests",
            "timestamp": datetime.now().isoformat(),
            "tests_run": [],
            "lime_explanations": [],
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

        # Add stored LIME explanations to results
        self.results['lime_explanations'] = _lime_explanations

        # Save overall results
        overall_file = os.path.join(results_dir, 'lime_test_results.json')
        with open(overall_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Save detailed LIME explanations separately
        if _lime_explanations:
            explanations_file = os.path.join(results_dir, 'lime_explanations_detailed.json')
            with open(explanations_file, 'w') as f:
                json.dump({
                    "timestamp": self.results['timestamp'],
                    "explanations": _lime_explanations
                }, f, indent=2)
            print(f"   - LIME explanations: {len(_lime_explanations)} saved")

        print(f"\n📊 LIME test results saved to: {results_dir}/")
        print(f"   - Overall: {self.results['summary']['passed']}/{self.results['summary']['total']} passed")


def pytest_configure(config):
    """Register the results plugin."""
    plugin = LIMEResultsPlugin()
    config.pluginmanager.register(plugin, "lime_results")

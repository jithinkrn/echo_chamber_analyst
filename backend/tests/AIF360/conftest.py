"""
Pytest configuration for AIF360 fairness tests.

⚠️ IMPORTANT: This creates REAL Django models for testing REAL backend code.

WHAT THESE FIXTURES DO:
=======================
1. Connect to Django database (test database)
2. Create REAL Django ORM models:
   - User (Django's built-in User model)
   - Brand (common/models.py)
   - Campaign (common/models.py)
   - Community (common/models.py) - HAS echo_score field
   - Thread (common/models.py) - HAS sentiment_score field
   - PainPoint (common/models.py)

3. These are NOT mock objects - they're REAL database records
4. Production code (agents/fairness_metrics.py) queries these REAL models
5. This proves Django ORM integration works

When you run backend server, it uses the EXACT same models and queries.
"""

import pytest
import os
import sys
import django
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ============================================================================
# IMPORT REAL PRODUCTION DJANGO MODELS
# These are the EXACT same models used by the backend server
# ============================================================================
from common.models import Brand, Campaign, Thread, ProcessedContent  # ← REAL models
from django.contrib.auth import get_user_model

User = get_user_model()

# Mark all tests in this module as requiring database
pytestmark = pytest.mark.django_db


@pytest.fixture(scope='function')
def test_user(db):
    """
    Create a REAL Django User model (same as production).

    This uses Django's User.objects.create_user() - the REAL ORM method
    that the backend server uses for creating users.
    """
    import uuid
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    # ← REAL Django ORM call (same as backend uses)
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="testpass123"
    )
    yield user
    user.delete()  # ← REAL Django ORM delete


@pytest.fixture(scope='function')
def test_brand(test_user, db):
    """
    Create a REAL Brand model (from common/models.py).

    This uses Brand.objects.create() - the REAL Django ORM method.
    When backend server creates a brand, it uses the exact same model.
    """
    import uuid
    # Use unique name to avoid conflicts
    brand_name = f"FairnessTestBrand_{uuid.uuid4().hex[:8]}"
    # ← REAL Django ORM call to create Brand (common/models.py)
    brand = Brand.objects.create(
        name=brand_name,
        industry="Technology"
    )
    yield brand
    # Cleanup with REAL Django ORM delete
    brand.delete()


@pytest.fixture(scope='function')
def test_campaigns_with_diverse_data(test_brand, test_user, db):
    """
    Create campaigns with diverse content using REAL Django models.

    ⚠️ IMPORTANT: This creates REAL database records, not mocks!

    Creates content with intentional diversity to test fairness:
    - Reddit communities (60% of data)
    - Discord communities (30% of data)
    - Forum communities (10% of data)

    REAL MODELS CREATED:
    - Campaign (common/models.py) - with budget_limit, campaign_type, owner
    - Community (common/models.py) - with echo_score, platform, member_count
    - Thread (common/models.py) - with sentiment_score, content, published_at

    Production code (agents/fairness_metrics.py) will query these models
    using the exact same Django ORM queries as the backend server.
    """
    from common.models import Community, PainPoint

    # ← REAL Django ORM call to create Campaign (common/models.py)
    campaign_auto = Campaign.objects.create(
        brand=test_brand,
        name="Automatic Campaign",
        campaign_type='automatic',
        status='active',
        budget_limit=Decimal('5000.00'),
        owner=test_user
    )

    # Create custom campaign
    campaign_custom = Campaign.objects.create(
        brand=test_brand,
        name="Custom Campaign",
        campaign_type='custom',
        status='active',
        budget_limit=Decimal('2000.00'),
        owner=test_user
    )

    # Create diverse communities with echo scores
    platforms = [
        ('reddit', 6, 70, 90),    # 6 communities from Reddit, echo range 70-90
        ('discord', 3, 50, 80),   # 3 communities from Discord, echo range 50-80
        ('forum', 1, 40, 60)      # 1 community from Forum, echo range 40-60
    ]

    all_communities = []
    all_threads = []
    all_content = []

    for platform, num_communities, echo_min, echo_max in platforms:
        for comm_idx in range(num_communities):
            # Alternate between campaigns
            campaign = campaign_auto if comm_idx % 2 == 0 else campaign_custom

            # Calculate echo score for this community
            echo_score = echo_min + (comm_idx * (echo_max - echo_min) // max(num_communities - 1, 1))

            # ← REAL Django ORM call to create Community (common/models.py)
            # This model HAS echo_score field (used by fairness checker)
            community = Community.objects.create(
                brand=test_brand,
                campaign=campaign,
                name=f"{platform}_community_{comm_idx}",
                platform=platform,
                url=f"https://{platform}.com/community_{comm_idx}",
                echo_score=echo_score,  # ← REAL field queried by fairness_metrics.py
                member_count=1000 + comm_idx * 100
            )
            all_communities.append(community)

            # Create threads for this community (5 threads per community)
            for thread_idx in range(5):
                # Varying sentiment based on platform
                if platform == 'reddit':
                    sentiment = -0.3 + (thread_idx % 5) * 0.1  # Range: -0.3 to 0.2
                elif platform == 'discord':
                    sentiment = -0.1 + (thread_idx % 5) * 0.1  # Range: -0.1 to 0.4
                else:  # forum
                    sentiment = 0.1 + (thread_idx % 5) * 0.1  # Range: 0.1 to 0.5

                # ← REAL Django ORM call to create Thread (common/models.py)
                # This model HAS sentiment_score field (used by fairness checker)
                thread = Thread.objects.create(
                    brand=test_brand,
                    campaign=campaign,
                    community=community,
                    thread_id=f"{platform}_c{comm_idx}_t{thread_idx}",
                    title=f"Thread {thread_idx} in {community.name}",
                    content=f"Content for thread {thread_idx}",
                    url=f"https://{platform}.com/thread_{comm_idx}_{thread_idx}",
                    author=f"user_{thread_idx}",
                    comment_count=10 + thread_idx,
                    upvotes=100 + thread_idx * 10,
                    published_at=datetime.now() - timedelta(days=thread_idx),
                    sentiment_score=sentiment  # ← REAL field queried by fairness_metrics.py
                )
                all_threads.append(thread)

    return {
        'brand': test_brand,
        'campaigns': [campaign_auto, campaign_custom],
        'communities': all_communities,
        'threads': all_threads
    }


@pytest.fixture(scope='function')
def test_budget_biased_campaigns(test_brand, test_user, db):
    """
    Create campaigns with varying budgets to test budget bias.
    """
    from common.models import Community

    campaigns = []
    all_communities = []

    # Low budget campaigns
    for i in range(3):
        campaign = Campaign.objects.create(
            brand=test_brand,
            name=f"Low Budget Campaign {i}",
            campaign_type='custom',
            status='active',
            budget_limit=Decimal('500.00'),
            owner=test_user
        )
        campaigns.append(campaign)

        # Create community for this campaign
        community = Community.objects.create(
            brand=test_brand,
            campaign=campaign,
            name=f"low_budget_community_{i}",
            platform='reddit',
            url=f"https://reddit.com/r/low_budget_{i}",
            echo_score=60,
            member_count=500
        )
        all_communities.append(community)

        # Add threads with lower success (negative sentiment)
        for j in range(5):
            thread = Thread.objects.create(
                brand=test_brand,
                campaign=campaign,
                community=community,
                thread_id=f"low_budget_{i}_{j}",
                title=f"Low budget thread {j}",
                content=f"Low budget content {j}",
                upvotes=10,
                published_at=datetime.now() - timedelta(days=j),
                sentiment_score=-0.4  # Negative sentiment
            )

    # High budget campaigns
    for i in range(3):
        campaign = Campaign.objects.create(
            brand=test_brand,
            name=f"High Budget Campaign {i}",
            campaign_type='automatic',
            status='active',
            budget_limit=Decimal('10000.00'),
            owner=test_user
        )
        campaigns.append(campaign)

        # Create community for this campaign
        community = Community.objects.create(
            brand=test_brand,
            campaign=campaign,
            name=f"high_budget_community_{i}",
            platform='reddit',
            url=f"https://reddit.com/r/high_budget_{i}",
            echo_score=40,
            member_count=5000
        )
        all_communities.append(community)

        # Add threads with higher success (positive sentiment)
        for j in range(5):
            thread = Thread.objects.create(
                brand=test_brand,
                campaign=campaign,
                community=community,
                thread_id=f"high_budget_{i}_{j}",
                title=f"High budget thread {j}",
                content=f"High budget content {j}",
                upvotes=100,
                published_at=datetime.now() - timedelta(days=j),
                sentiment_score=0.6  # Positive sentiment
            )

    return {
        'brand': test_brand,
        'campaigns': campaigns,
        'communities': all_communities
    }


# Pytest plugin to capture and save results
class AIF360ResultsPlugin:
    """Plugin to capture AIF360 test results."""

    def __init__(self):
        self.results = {
            "test_suite": "AIF360 Fairness Tests",
            "timestamp": datetime.now().isoformat(),
            "tests_run": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0
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

            # Update summary
            self.results['summary']['total'] += 1
            if report.outcome == 'passed':
                self.results['summary']['passed'] += 1
            elif report.outcome == 'failed':
                self.results['summary']['failed'] += 1
            elif report.outcome == 'skipped':
                self.results['summary']['skipped'] += 1

    def pytest_sessionfinish(self, session, exitstatus):
        """Save results to JSON files."""
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)

        # Save overall results
        overall_file = os.path.join(results_dir, 'aif360_test_results.json')
        with open(overall_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Separate brand and campaign results
        brand_tests = [t for t in self.results['tests_run'] if 'brand_fairness' in t['name']]
        campaign_tests = [t for t in self.results['tests_run'] if 'campaign_fairness' in t['name']]

        if brand_tests:
            brand_results = {
                "test_suite": "AIF360 Brand Fairness Tests",
                "timestamp": self.results['timestamp'],
                "tests_run": brand_tests,
                "summary": {
                    "total": len(brand_tests),
                    "passed": len([t for t in brand_tests if t['outcome'] == 'passed']),
                    "failed": len([t for t in brand_tests if t['outcome'] == 'failed']),
                }
            }
            brand_file = os.path.join(results_dir, 'brand_fairness_results.json')
            with open(brand_file, 'w') as f:
                json.dump(brand_results, f, indent=2)

        if campaign_tests:
            campaign_results = {
                "test_suite": "AIF360 Campaign Fairness Tests",
                "timestamp": self.results['timestamp'],
                "tests_run": campaign_tests,
                "summary": {
                    "total": len(campaign_tests),
                    "passed": len([t for t in campaign_tests if t['outcome'] == 'passed']),
                    "failed": len([t for t in campaign_tests if t['outcome'] == 'failed']),
                }
            }
            campaign_file = os.path.join(results_dir, 'campaign_fairness_results.json')
            with open(campaign_file, 'w') as f:
                json.dump(campaign_results, f, indent=2)

        print(f"\n📊 AIF360 test results saved to: {results_dir}/")
        print(f"   - Overall: {self.results['summary']['passed']}/{self.results['summary']['total']} passed")


def pytest_configure(config):
    """Register the results plugin."""
    plugin = AIF360ResultsPlugin()
    config.pluginmanager.register(plugin, "aif360_results")


# ============================================================================
# NEW FIXTURE FOR AIF360 FAIRNESS TESTING
# ============================================================================

@pytest.fixture(scope='function')
def diverse_brand_dataset(db):
    """
    Create a diverse set of brands for AIF360 fairness testing.

    Returns:
        Tuple of (brands_data, user)

    brands_data is a list of dicts with:
        - brand: Brand instance
        - kpis: KPI dictionary
        - communities: List of community data
        - pain_points: List of pain point data
        - budget_category: 'Small', 'Medium', or 'Large'
        - budget_category_code: 0.0 (Small/Medium) or 1.0 (Large)
    """
    # Create test user
    user = User.objects.create_user(
        username='aif360_test_user',
        email='aif360@test.com',
        password='testpass123'
    )

    brands_data = []

    # Define diverse brand characteristics
    brand_configs = [
        # Technology brands
        {'industry': 'Technology', 'budget': 'Large', 'sentiment': -0.4, 'echo': 75},
        {'industry': 'Technology', 'budget': 'Medium', 'sentiment': -0.3, 'echo': 70},
        {'industry': 'Technology', 'budget': 'Small', 'sentiment': -0.5, 'echo': 80},

        # Fashion brands
        {'industry': 'Fashion', 'budget': 'Large', 'sentiment': -0.35, 'echo': 72},
        {'industry': 'Fashion', 'budget': 'Medium', 'sentiment': -0.4, 'echo': 78},
        {'industry': 'Fashion', 'budget': 'Small', 'sentiment': -0.6, 'echo': 85},

        # Food brands
        {'industry': 'Food', 'budget': 'Large', 'sentiment': -0.3, 'echo': 68},
        {'industry': 'Food', 'budget': 'Medium', 'sentiment': -0.45, 'echo': 75},
        {'industry': 'Food', 'budget': 'Small', 'sentiment': -0.55, 'echo': 82},

        # Healthcare brands
        {'industry': 'Healthcare', 'budget': 'Large', 'sentiment': -0.25, 'echo': 65},
        {'industry': 'Healthcare', 'budget': 'Medium', 'sentiment': -0.4, 'echo': 73},
        {'industry': 'Healthcare', 'budget': 'Small', 'sentiment': -0.5, 'echo': 79},
    ]

    for config in brand_configs:
        # Create Brand (Note: Brand model doesn't have created_by field)
        brand = Brand.objects.create(
            name=f"{config['industry']} {config['budget']} Brand",
            industry=config['industry']
        )

        # Budget category code (for AIF360)
        budget_code = 1.0 if config['budget'] == 'Large' else 0.0

        # KPIs
        kpis = {
            'avg_sentiment': config['sentiment'],
            'avg_echo_score': config['echo'],
            'total_mentions': 500 if config['budget'] == 'Large' else 200,
            'top_pain_point': 'Service issues',
            'engagement_rate': 40.0 if config['budget'] == 'Large' else 25.0,
            'community_count': 5 if config['budget'] == 'Large' else 3
        }

        # Communities
        communities = [
            {
                'community_name': f'r/{config["industry"]}Community1',
                'platform': 'Reddit',
                'echo_score': config['echo'] + 5,
                'sentiment_score': config['sentiment'] - 0.1,
                'member_count': 8000 if config['budget'] == 'Large' else 3000,
                'post_count': 200 if config['budget'] == 'Large' else 80
            },
            {
                'community_name': f'r/{config["industry"]}Community2',
                'platform': 'Reddit',
                'echo_score': config['echo'] - 5,
                'sentiment_score': config['sentiment'] + 0.1,
                'member_count': 5000 if config['budget'] == 'Large' else 2000,
                'post_count': 150 if config['budget'] == 'Large' else 60
            }
        ]

        # Pain points
        pain_points = [
            {
                'keyword': 'Customer service',
                'mention_count': 120 if config['budget'] == 'Large' else 50,
                'sentiment_score': -0.7,
                'growth_percentage': 25.0
            },
            {
                'keyword': 'Product quality',
                'mention_count': 95 if config['budget'] == 'Large' else 40,
                'sentiment_score': -0.6,
                'growth_percentage': 18.0
            },
            {
                'keyword': 'Delivery delays',
                'mention_count': 80 if config['budget'] == 'Large' else 35,
                'sentiment_score': -0.65,
                'growth_percentage': 15.0
            }
        ]

        brands_data.append({
            'brand': brand,
            'kpis': kpis,
            'communities': communities,
            'pain_points': pain_points,
            'budget_category': config['budget'],
            'budget_category_code': budget_code
        })

    yield brands_data, user

    # Cleanup
    for brand_data in brands_data:
        brand_data['brand'].delete()
    user.delete()

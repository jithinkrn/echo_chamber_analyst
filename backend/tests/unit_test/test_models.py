"""
Unit tests for Django models.

These tests verify the core functionality of all models without altering application code.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import IntegrityError
from datetime import datetime, timedelta
from decimal import Decimal

from common.models import (
    Brand, Competitor, Campaign, Source, RawContent, ProcessedContent,
    Insight, Influencer, AuditLog, AgentMetrics,
    Community, PainPoint, Thread, DashboardMetrics, SystemSettings
)


@pytest.mark.django_db
class TestBrandModel(TestCase):
    """Test Brand model functionality."""

    def setUp(self):
        """Set up test data."""
        self.brand_data = {
            'name': 'TestBrand',
            'description': 'A test brand for unit testing',
            'website': 'https://testbrand.com',
            'industry': 'Technology',
            'headquarters': 'San Francisco, CA'
        }

    def test_brand_creation(self):
        """Test creating a brand."""
        brand = Brand.objects.create(**self.brand_data)

        self.assertEqual(brand.name, 'TestBrand')
        self.assertEqual(brand.industry, 'Technology')
        self.assertTrue(brand.is_active)
        self.assertIsNotNone(brand.id)
        self.assertIsNotNone(brand.created_at)

    def test_brand_unique_name(self):
        """Test that brand names must be unique."""
        Brand.objects.create(**self.brand_data)

        with self.assertRaises(IntegrityError):
            Brand.objects.create(**self.brand_data)

    def test_brand_str_representation(self):
        """Test brand string representation."""
        brand = Brand.objects.create(**self.brand_data)
        self.assertEqual(str(brand), 'TestBrand')

    def test_brand_json_fields(self):
        """Test brand JSON fields."""
        brand = Brand.objects.create(
            name='JsonTestBrand',
            social_handles={'twitter': '@testbrand', 'instagram': '@testbrand'},
            primary_keywords=['test', 'brand'],
            product_keywords=['product1', 'product2'],
            exclude_keywords=['spam', 'fake'],
            sources=['reddit', 'discord']
        )

        self.assertEqual(brand.social_handles['twitter'], '@testbrand')
        self.assertEqual(len(brand.primary_keywords), 2)
        self.assertIn('product1', brand.product_keywords)
        self.assertEqual(len(brand.sources), 2)

    def test_brand_default_values(self):
        """Test brand default values."""
        brand = Brand.objects.create(name='MinimalBrand')

        self.assertEqual(brand.social_handles, {})
        self.assertEqual(brand.primary_keywords, [])
        self.assertEqual(brand.product_keywords, [])
        self.assertEqual(brand.exclude_keywords, [])
        self.assertEqual(brand.sources, [])
        self.assertTrue(brand.is_active)


@pytest.mark.django_db
class TestCompetitorModel(TestCase):
    """Test Competitor model functionality."""

    def setUp(self):
        """Set up test data."""
        self.brand = Brand.objects.create(name='TestBrand')
        self.competitor_data = {
            'brand': self.brand,
            'name': 'CompetitorBrand',
            'description': 'A competing brand',
            'website': 'https://competitor.com'
        }

    def test_competitor_creation(self):
        """Test creating a competitor."""
        competitor = Competitor.objects.create(**self.competitor_data)

        self.assertEqual(competitor.name, 'CompetitorBrand')
        self.assertEqual(competitor.brand, self.brand)
        self.assertTrue(competitor.is_active)

    def test_competitor_unique_together(self):
        """Test that brand+name must be unique."""
        Competitor.objects.create(**self.competitor_data)

        with self.assertRaises(IntegrityError):
            Competitor.objects.create(**self.competitor_data)

    def test_competitor_cascade_delete(self):
        """Test that competitors are deleted when brand is deleted."""
        competitor = Competitor.objects.create(**self.competitor_data)
        brand_id = self.brand.id

        self.brand.delete()

        self.assertFalse(Competitor.objects.filter(brand_id=brand_id).exists())

    def test_competitor_str_representation(self):
        """Test competitor string representation."""
        competitor = Competitor.objects.create(**self.competitor_data)
        expected = f"CompetitorBrand (competitor of TestBrand)"
        self.assertEqual(str(competitor), expected)


@pytest.mark.django_db
class TestCampaignModel(TestCase):
    """Test Campaign model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.campaign_data = {
            'name': 'Test Campaign',
            'description': 'A test campaign',
            'brand': self.brand,
            'owner': self.user,
            'status': 'active',
            'campaign_type': 'custom'
        }

    def test_campaign_creation(self):
        """Test creating a campaign."""
        campaign = Campaign.objects.create(**self.campaign_data)

        self.assertEqual(campaign.name, 'Test Campaign')
        self.assertEqual(campaign.status, 'active')
        self.assertEqual(campaign.campaign_type, 'custom')
        self.assertTrue(campaign.schedule_enabled)
        self.assertEqual(campaign.schedule_interval, 3600)

    def test_campaign_status_choices(self):
        """Test campaign status choices."""
        valid_statuses = ['active', 'paused', 'completed', 'error']

        for status in valid_statuses:
            campaign = Campaign.objects.create(
                name=f'Campaign {status}',
                owner=self.user,
                status=status
            )
            self.assertEqual(campaign.status, status)

    def test_campaign_type_choices(self):
        """Test campaign type choices."""
        campaign_auto = Campaign.objects.create(
            name='Auto Campaign',
            owner=self.user,
            campaign_type='automatic'
        )
        self.assertEqual(campaign_auto.campaign_type, 'automatic')

        campaign_custom = Campaign.objects.create(
            name='Custom Campaign',
            owner=self.user,
            campaign_type='custom'
        )
        self.assertEqual(campaign_custom.campaign_type, 'custom')

    def test_campaign_json_fields(self):
        """Test campaign JSON fields."""
        campaign = Campaign.objects.create(
            name='JSON Campaign',
            owner=self.user,
            keywords=['keyword1', 'keyword2'],
            sources=['reddit', 'discord'],
            exclude_keywords=['spam'],
            monitored_communities=['community1', 'community2'],
            metadata={'test': 'data', 'score': 95}
        )

        self.assertEqual(len(campaign.keywords), 2)
        self.assertEqual(len(campaign.sources), 2)
        self.assertEqual(campaign.metadata['score'], 95)

    def test_campaign_default_values(self):
        """Test campaign default values."""
        campaign = Campaign.objects.create(
            name='Default Campaign',
            owner=self.user
        )

        self.assertEqual(campaign.status, 'active')
        self.assertEqual(campaign.campaign_type, 'custom')
        self.assertTrue(campaign.schedule_enabled)
        self.assertEqual(campaign.schedule_interval, 3600)
        self.assertEqual(campaign.collection_months, 6)
        self.assertEqual(campaign.daily_budget, Decimal('10.00'))
        self.assertEqual(campaign.current_spend, Decimal('0.00'))

    def test_campaign_budget_tracking(self):
        """Test campaign budget tracking."""
        campaign = Campaign.objects.create(
            name='Budget Campaign',
            owner=self.user,
            daily_budget=Decimal('100.00'),
            current_spend=Decimal('45.50'),
            budget_limit=Decimal('1000.00')
        )

        self.assertEqual(campaign.daily_budget, Decimal('100.00'))
        self.assertEqual(campaign.current_spend, Decimal('45.50'))
        self.assertEqual(campaign.budget_limit, Decimal('1000.00'))


@pytest.mark.django_db
class TestSourceModel(TestCase):
    """Test Source model functionality."""

    def setUp(self):
        """Set up test data."""
        self.source_data = {
            'name': 'Test Subreddit',
            'source_type': 'reddit',
            'url': 'https://reddit.com/r/test',
            'description': 'A test subreddit'
        }

    def test_source_creation(self):
        """Test creating a source."""
        source = Source.objects.create(**self.source_data)

        self.assertEqual(source.name, 'Test Subreddit')
        self.assertEqual(source.source_type, 'reddit')
        self.assertTrue(source.is_active)
        self.assertEqual(source.rate_limit, 60)

    def test_source_types(self):
        """Test different source types."""
        source_types = ['reddit', 'discord', 'forum', 'website']

        for i, stype in enumerate(source_types):
            source = Source.objects.create(
                name=f'Test {stype}',
                source_type=stype,
                url=f'https://example.com/{stype}/{i}'
            )
            self.assertEqual(source.source_type, stype)

    def test_source_unique_together(self):
        """Test that source_type+url must be unique."""
        Source.objects.create(**self.source_data)

        with self.assertRaises(IntegrityError):
            Source.objects.create(**self.source_data)

    def test_source_str_representation(self):
        """Test source string representation."""
        source = Source.objects.create(**self.source_data)
        self.assertEqual(str(source), 'Test Subreddit (reddit)')

    def test_source_config_field(self):
        """Test source config JSON field."""
        source = Source.objects.create(
            name='Configured Source',
            source_type='reddit',
            url='https://reddit.com/r/configured',
            config={'api_key': 'test123', 'limit': 100}
        )

        self.assertEqual(source.config['api_key'], 'test123')
        self.assertEqual(source.config['limit'], 100)


@pytest.mark.django_db
class TestCommunityModel(TestCase):
    """Test Community model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user,
            brand=self.brand
        )

    def test_community_creation(self):
        """Test creating a community."""
        community = Community.objects.create(
            name='TestCommunity',
            platform='reddit',
            url='https://reddit.com/r/test',
            campaign=self.campaign,
            brand=self.brand,
            member_count=5000
        )

        self.assertEqual(community.name, 'TestCommunity')
        self.assertEqual(community.platform, 'reddit')
        self.assertEqual(community.member_count, 5000)
        self.assertEqual(community.echo_score, 0.0)
        self.assertTrue(community.is_active)

    def test_community_platform_choices(self):
        """Test community platform choices."""
        platforms = ['reddit', 'discord', 'tiktok', 'forum', 'twitter']

        for i, platform in enumerate(platforms):
            community = Community.objects.create(
                name=f'Community{i}',
                platform=platform,
                url=f'https://{platform}.com/test{i}',
                campaign=self.campaign
            )
            self.assertEqual(community.platform, platform)

    def test_community_influencer_fields(self):
        """Test community influencer tracking fields."""
        community = Community.objects.create(
            name='InfluencerCommunity',
            platform='reddit',
            url='https://reddit.com/r/influencer',
            campaign=self.campaign,
            key_influencer='top_user',
            influencer_post_count=150,
            influencer_engagement=5000
        )

        self.assertEqual(community.key_influencer, 'top_user')
        self.assertEqual(community.influencer_post_count, 150)
        self.assertEqual(community.influencer_engagement, 5000)

    def test_community_unique_together(self):
        """Test community unique constraint."""
        Community.objects.create(
            name='UniqueCommunity',
            platform='reddit',
            url='https://reddit.com/r/unique',
            campaign=self.campaign
        )

        with self.assertRaises(IntegrityError):
            Community.objects.create(
                name='UniqueCommunity',
                platform='reddit',
                url='https://reddit.com/r/unique2',
                campaign=self.campaign
            )

    def test_community_str_representation(self):
        """Test community string representation."""
        community = Community.objects.create(
            name='StrTestCommunity',
            platform='reddit',
            url='https://reddit.com/r/strtest',
            campaign=self.campaign
        )
        self.assertEqual(str(community), 'StrTestCommunity (reddit)')


@pytest.mark.django_db
class TestPainPointModel(TestCase):
    """Test PainPoint model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user,
            brand=self.brand
        )
        self.community = Community.objects.create(
            name='TestCommunity',
            platform='reddit',
            url='https://reddit.com/r/test',
            campaign=self.campaign
        )

    def test_pain_point_creation(self):
        """Test creating a pain point."""
        pain_point = PainPoint.objects.create(
            keyword='slow_performance',
            campaign=self.campaign,
            community=self.community,
            brand=self.brand,
            month_year='2024-11',
            mention_count=50,
            sentiment_score=-0.5,
            growth_percentage=15.5,
            heat_level=4
        )

        self.assertEqual(pain_point.keyword, 'slow_performance')
        self.assertEqual(pain_point.mention_count, 50)
        self.assertEqual(pain_point.sentiment_score, -0.5)
        self.assertEqual(pain_point.heat_level, 4)

    def test_pain_point_unique_together(self):
        """Test pain point unique constraint."""
        PainPoint.objects.create(
            keyword='test_keyword',
            campaign=self.campaign,
            community=self.community,
            month_year='2024-11'
        )

        with self.assertRaises(IntegrityError):
            PainPoint.objects.create(
                keyword='test_keyword',
                campaign=self.campaign,
                community=self.community,
                month_year='2024-11'
            )

    def test_pain_point_json_field(self):
        """Test pain point related_keywords JSON field."""
        pain_point = PainPoint.objects.create(
            keyword='main_keyword',
            campaign=self.campaign,
            community=self.community,
            related_keywords=['related1', 'related2', 'related3']
        )

        self.assertEqual(len(pain_point.related_keywords), 3)
        self.assertIn('related1', pain_point.related_keywords)

    def test_pain_point_str_representation(self):
        """Test pain point string representation."""
        pain_point = PainPoint.objects.create(
            keyword='test_pain',
            campaign=self.campaign,
            community=self.community,
            mention_count=25,
            growth_percentage=10.5
        )
        expected = "test_pain (Growth: 10.5%, 25 mentions)"
        self.assertEqual(str(pain_point), expected)


@pytest.mark.django_db
class TestThreadModel(TestCase):
    """Test Thread model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user,
            brand=self.brand
        )
        self.community = Community.objects.create(
            name='TestCommunity',
            platform='reddit',
            url='https://reddit.com/r/test',
            campaign=self.campaign
        )

    def test_thread_creation(self):
        """Test creating a thread."""
        thread = Thread.objects.create(
            thread_id='abc123',
            title='Test Thread Title',
            content='This is test content for the thread.',
            url='https://reddit.com/r/test/comments/abc123',
            community=self.community,
            campaign=self.campaign,
            brand=self.brand,
            author='test_author',
            published_at=timezone.now(),
            upvotes=100,
            downvotes=5,
            comment_count=25
        )

        self.assertEqual(thread.thread_id, 'abc123')
        self.assertEqual(thread.title, 'Test Thread Title')
        self.assertEqual(thread.upvotes, 100)
        self.assertEqual(thread.comment_count, 25)

    def test_thread_unique_together(self):
        """Test thread unique constraint."""
        Thread.objects.create(
            thread_id='unique123',
            title='Unique Thread',
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='author',
            published_at=timezone.now()
        )

        with self.assertRaises(IntegrityError):
            Thread.objects.create(
                thread_id='unique123',
                title='Another Thread',
                content='Different content',
                community=self.community,
                campaign=self.campaign,
                author='another_author',
                published_at=timezone.now()
            )

    def test_thread_scores(self):
        """Test thread scoring fields."""
        thread = Thread.objects.create(
            thread_id='score123',
            title='Score Thread',
            content='Content with scores',
            community=self.community,
            campaign=self.campaign,
            author='author',
            published_at=timezone.now(),
            echo_score=75.5,
            sentiment_score=0.8,
            engagement_rate=12.5,
            controversy_score=3.2
        )

        self.assertEqual(thread.echo_score, 75.5)
        self.assertEqual(thread.sentiment_score, 0.8)
        self.assertEqual(thread.engagement_rate, 12.5)
        self.assertEqual(thread.controversy_score, 3.2)

    def test_thread_llm_fields(self):
        """Test thread LLM processing fields."""
        thread = Thread.objects.create(
            thread_id='llm123',
            title='LLM Thread',
            content='Content to be processed',
            community=self.community,
            campaign=self.campaign,
            author='author',
            published_at=timezone.now(),
            llm_summary='This is an AI-generated summary.',
            token_count=150,
            processing_cost=Decimal('0.0025')
        )

        self.assertEqual(thread.llm_summary, 'This is an AI-generated summary.')
        self.assertEqual(thread.token_count, 150)
        self.assertEqual(thread.processing_cost, Decimal('0.0025'))


@pytest.mark.django_db
class TestInfluencerModel(TestCase):
    """Test Influencer model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user,
            brand=self.brand
        )

    def test_influencer_creation(self):
        """Test creating an influencer."""
        influencer = Influencer.objects.create(
            campaign=self.campaign,
            brand=self.brand,
            username='test_influencer',
            display_name='Test Influencer',
            source_type='reddit',
            platform='reddit',
            profile_url='https://reddit.com/u/test_influencer',
            influence_score=85.5,
            reach_score=90.0,
            authority_score=80.0,
            advocacy_score=75.0,
            relevance_score=88.0
        )

        self.assertEqual(influencer.username, 'test_influencer')
        self.assertEqual(influencer.influence_score, 85.5)
        self.assertEqual(influencer.platform, 'reddit')

    def test_influencer_unique_together(self):
        """Test influencer unique constraint."""
        Influencer.objects.create(
            campaign=self.campaign,
            username='unique_influencer',
            source_type='reddit'
        )

        with self.assertRaises(IntegrityError):
            Influencer.objects.create(
                campaign=self.campaign,
                username='unique_influencer',
                source_type='reddit'
            )

    def test_influencer_metrics(self):
        """Test influencer engagement metrics."""
        influencer = Influencer.objects.create(
            campaign=self.campaign,
            username='metrics_influencer',
            source_type='reddit',
            total_karma=50000,
            total_posts=500,
            total_comments=2000,
            avg_post_score=150.5,
            avg_engagement_rate=5.5
        )

        self.assertEqual(influencer.total_karma, 50000)
        self.assertEqual(influencer.total_posts, 500)
        self.assertEqual(influencer.avg_post_score, 150.5)

    def test_influencer_brand_sentiment(self):
        """Test influencer brand sentiment tracking."""
        influencer = Influencer.objects.create(
            campaign=self.campaign,
            username='sentiment_influencer',
            source_type='reddit',
            sentiment_towards_brand=0.75,
            brand_mention_count=25,
            brand_mention_rate=15.5
        )

        self.assertEqual(influencer.sentiment_towards_brand, 0.75)
        self.assertEqual(influencer.brand_mention_count, 25)
        self.assertEqual(influencer.brand_mention_rate, 15.5)


@pytest.mark.django_db
class TestSystemSettingsModel(TestCase):
    """Test SystemSettings model functionality."""

    def test_system_settings_singleton(self):
        """Test that only one SystemSettings instance exists."""
        settings1 = SystemSettings.objects.create(
            custom_campaign_interval=7200,
            auto_campaign_interval=3600
        )

        settings2 = SystemSettings.objects.create(
            custom_campaign_interval=10800,
            auto_campaign_interval=5400
        )

        # Should only have one instance
        self.assertEqual(SystemSettings.objects.count(), 1)

        # The second save should have updated the first
        settings = SystemSettings.objects.get(pk=1)
        self.assertEqual(settings.custom_campaign_interval, 10800)
        self.assertEqual(settings.auto_campaign_interval, 5400)

    def test_system_settings_get_settings(self):
        """Test get_settings class method."""
        settings = SystemSettings.get_settings()

        self.assertIsNotNone(settings)
        self.assertEqual(settings.pk, 1)

        # Should return the same instance
        settings2 = SystemSettings.get_settings()
        self.assertEqual(settings.pk, settings2.pk)

    def test_system_settings_default_values(self):
        """Test SystemSettings default values."""
        settings = SystemSettings.get_settings()

        self.assertEqual(settings.custom_campaign_interval, 3600)
        self.assertEqual(settings.auto_campaign_interval, 3600)


@pytest.mark.django_db
class TestDashboardMetricsModel(TestCase):
    """Test DashboardMetrics model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )

    def test_dashboard_metrics_creation(self):
        """Test creating dashboard metrics."""
        metrics = DashboardMetrics.objects.create(
            date=timezone.now().date(),
            campaign=self.campaign,
            active_campaigns=5,
            high_echo_communities=3,
            high_echo_change_percent=15.5,
            new_pain_points_above_50=2,
            new_pain_points_change=1,
            positivity_ratio=0.65,
            positivity_change_pp=2.5,
            llm_tokens_used=50000,
            llm_cost_usd=5.50
        )

        self.assertEqual(metrics.active_campaigns, 5)
        self.assertEqual(metrics.high_echo_communities, 3)
        self.assertEqual(metrics.positivity_ratio, 0.65)
        self.assertEqual(metrics.llm_tokens_used, 50000)

    def test_dashboard_metrics_unique_together(self):
        """Test dashboard metrics unique constraint."""
        date = timezone.now().date()

        DashboardMetrics.objects.create(
            date=date,
            campaign=self.campaign,
            active_campaigns=5
        )

        with self.assertRaises(IntegrityError):
            DashboardMetrics.objects.create(
                date=date,
                campaign=self.campaign,
                active_campaigns=6
            )

    def test_dashboard_metrics_str_representation(self):
        """Test dashboard metrics string representation."""
        date = timezone.now().date()
        metrics = DashboardMetrics.objects.create(
            date=date,
            campaign=self.campaign
        )
        expected = f"Dashboard metrics for Test Campaign on {date}"
        self.assertEqual(str(metrics), expected)

"""
Unit tests for API serializers.

These tests verify serializer functionality without altering application code.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from decimal import Decimal

from common.models import (
    Brand, Competitor, Campaign, Source, Influencer,
    Community, PainPoint, Thread, DashboardMetrics
)
from api.serializers import (
    BrandSerializer, CompetitorSerializer, CampaignSerializer,
    SourceSerializer, InfluencerSerializer, CommunitySerializer,
    PainPointSerializer, ThreadSerializer, DashboardMetricsSerializer,
    UserSerializer
)


@pytest.mark.django_db
class TestBrandSerializer(TestCase):
    """Test BrandSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.brand = Brand.objects.create(
            name='TestBrand',
            description='Test Description',
            website='https://testbrand.com',
            industry='Technology'
        )

    def test_brand_serialization(self):
        """Test serializing a brand."""
        serializer = BrandSerializer(self.brand)
        data = serializer.data

        self.assertEqual(data['name'], 'TestBrand')
        self.assertEqual(data['industry'], 'Technology')
        self.assertIn('id', data)
        self.assertIn('created_at', data)

    def test_brand_deserialization(self):
        """Test deserializing brand data."""
        data = {
            'name': 'NewBrand',
            'description': 'New test brand',
            'website': 'https://newbrand.com',
            'industry': 'Finance'
        }

        serializer = BrandSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        brand = serializer.save()
        self.assertEqual(brand.name, 'NewBrand')
        self.assertEqual(brand.industry, 'Finance')

    def test_brand_validation(self):
        """Test brand validation."""
        # Missing required name field
        data = {
            'description': 'Missing name'
        }

        serializer = BrandSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)


@pytest.mark.django_db
class TestCompetitorSerializer(TestCase):
    """Test CompetitorSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.brand = Brand.objects.create(name='TestBrand')
        self.competitor = Competitor.objects.create(
            brand=self.brand,
            name='CompetitorBrand',
            website='https://competitor.com'
        )

    def test_competitor_serialization(self):
        """Test serializing a competitor."""
        serializer = CompetitorSerializer(self.competitor)
        data = serializer.data

        self.assertEqual(data['name'], 'CompetitorBrand')
        self.assertEqual(data['brand_name'], 'TestBrand')
        self.assertIn('id', data)

    def test_competitor_deserialization(self):
        """Test deserializing competitor data."""
        data = {
            'brand': self.brand.id,
            'name': 'NewCompetitor',
            'website': 'https://newcompetitor.com'
        }

        serializer = CompetitorSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        competitor = serializer.save()
        self.assertEqual(competitor.name, 'NewCompetitor')
        self.assertEqual(competitor.brand, self.brand)


@pytest.mark.django_db
class TestCampaignSerializer(TestCase):
    """Test CampaignSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.factory = APIRequestFactory()

    def test_campaign_serialization(self):
        """Test serializing a campaign."""
        campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user,
            brand=self.brand,
            status='active'
        )

        serializer = CampaignSerializer(campaign)
        data = serializer.data

        self.assertEqual(data['name'], 'Test Campaign')
        self.assertEqual(data['owner_name'], 'testuser')
        self.assertEqual(data['brand_name'], 'TestBrand')
        self.assertEqual(data['status'], 'active')

    def test_campaign_deserialization(self):
        """Test deserializing campaign data."""
        request = self.factory.post('/api/campaigns/')
        request.user = self.user

        data = {
            'name': 'New Campaign',
            'brand': self.brand.id,
            'status': 'active',
            'keywords': ['test', 'campaign']
        }

        serializer = CampaignSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        campaign = serializer.save()
        self.assertEqual(campaign.name, 'New Campaign')
        self.assertEqual(campaign.owner, self.user)

    def test_campaign_read_only_fields(self):
        """Test campaign read-only fields."""
        campaign = Campaign.objects.create(
            name='ReadOnly Campaign',
            owner=self.user,
            current_spend=Decimal('50.00')
        )

        data = {
            'name': 'Updated Campaign',
            'current_spend': Decimal('100.00')  # Should not update
        }

        serializer = CampaignSerializer(campaign, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_campaign = serializer.save()
        # current_spend should not have changed (it's read-only)
        self.assertEqual(updated_campaign.current_spend, Decimal('50.00'))


@pytest.mark.django_db
class TestCommunitySerializer(TestCase):
    """Test CommunitySerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='TestCommunity',
            platform='reddit',
            url='https://reddit.com/r/test',
            campaign=self.campaign,
            member_count=5000,
            echo_score=75.5
        )

    def test_community_serialization(self):
        """Test serializing a community."""
        serializer = CommunitySerializer(self.community)
        data = serializer.data

        self.assertEqual(data['name'], 'TestCommunity')
        self.assertEqual(data['platform'], 'reddit')
        self.assertEqual(data['member_count'], 5000)
        self.assertEqual(float(data['echo_score']), 75.5)

    def test_community_deserialization(self):
        """Test deserializing community data."""
        data = {
            'name': 'NewCommunity',
            'platform': 'discord',
            'url': 'https://discord.gg/newcommunity',
            'campaign': self.campaign.id,
            'member_count': 10000
        }

        serializer = CommunitySerializer(data=data)
        self.assertTrue(serializer.is_valid())

        community = serializer.save()
        self.assertEqual(community.name, 'NewCommunity')
        self.assertEqual(community.platform, 'discord')
        self.assertEqual(community.member_count, 10000)


@pytest.mark.django_db
class TestPainPointSerializer(TestCase):
    """Test PainPointSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='TestCommunity',
            platform='reddit',
            url='https://reddit.com/r/test',
            campaign=self.campaign
        )
        self.pain_point = PainPoint.objects.create(
            keyword='slow_performance',
            campaign=self.campaign,
            community=self.community,
            mention_count=50,
            sentiment_score=-0.5,
            growth_percentage=15.5
        )

    def test_pain_point_serialization(self):
        """Test serializing a pain point."""
        serializer = PainPointSerializer(self.pain_point)
        data = serializer.data

        self.assertEqual(data['keyword'], 'slow_performance')
        self.assertEqual(data['mention_count'], 50)
        self.assertEqual(float(data['sentiment_score']), -0.5)
        self.assertEqual(data['community_name'], 'TestCommunity')
        self.assertEqual(data['campaign_name'], 'Test Campaign')

    def test_pain_point_deserialization(self):
        """Test deserializing pain point data."""
        data = {
            'keyword': 'high_price',
            'campaign': self.campaign.id,
            'community': self.community.id,
            'mention_count': 25,
            'sentiment_score': -0.7,
            'heat_level': 3
        }

        serializer = PainPointSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        pain_point = serializer.save()
        self.assertEqual(pain_point.keyword, 'high_price')
        self.assertEqual(pain_point.mention_count, 25)


@pytest.mark.django_db
class TestThreadSerializer(TestCase):
    """Test ThreadSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='TestCommunity',
            platform='reddit',
            url='https://reddit.com/r/test',
            campaign=self.campaign
        )

    def test_thread_serialization(self):
        """Test serializing a thread."""
        thread = Thread.objects.create(
            thread_id='abc123',
            title='Test Thread',
            content='Test content',
            community=self.community,
            campaign=self.campaign,
            author='test_author',
            published_at=timezone.now(),
            upvotes=100
        )

        serializer = ThreadSerializer(thread)
        data = serializer.data

        self.assertEqual(data['thread_id'], 'abc123')
        self.assertEqual(data['title'], 'Test Thread')
        self.assertEqual(data['community_name'], 'TestCommunity')
        self.assertEqual(data['upvotes'], 100)

    def test_thread_with_pain_points(self):
        """Test serializing a thread with pain points."""
        thread = Thread.objects.create(
            thread_id='pp123',
            title='Thread with Pain Points',
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='author',
            published_at=timezone.now()
        )

        pain_point1 = PainPoint.objects.create(
            keyword='issue1',
            campaign=self.campaign,
            community=self.community
        )
        pain_point2 = PainPoint.objects.create(
            keyword='issue2',
            campaign=self.campaign,
            community=self.community
        )

        thread.pain_points.add(pain_point1, pain_point2)

        serializer = ThreadSerializer(thread)
        data = serializer.data

        self.assertEqual(len(data['pain_point_chips']), 2)
        self.assertIn('issue1', data['pain_point_chips'])
        self.assertIn('issue2', data['pain_point_chips'])


@pytest.mark.django_db
class TestInfluencerSerializer(TestCase):
    """Test InfluencerSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )

    def test_influencer_serialization(self):
        """Test serializing an influencer."""
        influencer = Influencer.objects.create(
            campaign=self.campaign,
            username='test_influencer',
            display_name='Test Influencer',
            source_type='reddit',
            influence_score=85.5
        )

        serializer = InfluencerSerializer(influencer)
        data = serializer.data

        self.assertEqual(data['username'], 'test_influencer')
        self.assertEqual(data['display_name'], 'Test Influencer')
        self.assertEqual(float(data['influence_score']), 85.5)
        self.assertEqual(data['campaign_name'], 'Test Campaign')

    def test_influencer_deserialization(self):
        """Test deserializing influencer data."""
        data = {
            'campaign': self.campaign.id,
            'username': 'new_influencer',
            'source_type': 'reddit',
            'influence_score': 90.0,
            'reach_score': 85.0
        }

        serializer = InfluencerSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        influencer = serializer.save()
        self.assertEqual(influencer.username, 'new_influencer')
        self.assertEqual(influencer.influence_score, 90.0)


@pytest.mark.django_db
class TestUserSerializer(TestCase):
    """Test UserSerializer functionality."""

    def test_user_serialization(self):
        """Test serializing a user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass'
        )

        serializer = UserSerializer(user)
        data = serializer.data

        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertIn('id', data)
        self.assertNotIn('password', data)  # Should not expose password

    def test_user_read_only_fields(self):
        """Test user read-only fields."""
        user = User.objects.create_user(
            username='readonly',
            password='testpass'
        )

        # Try to update read-only fields
        data = {
            'username': 'readonly',
            'email': 'new@example.com',
            'date_joined': '2020-01-01T00:00:00Z'  # Read-only
        }

        serializer = UserSerializer(user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        # date_joined should not have been updated
        updated_user = serializer.save()
        self.assertNotEqual(
            updated_user.date_joined.strftime('%Y-%m-%d'),
            '2020-01-01'
        )


@pytest.mark.django_db
class TestDashboardMetricsSerializer(TestCase):
    """Test DashboardMetricsSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            owner=self.user
        )

    def test_dashboard_metrics_serialization(self):
        """Test serializing dashboard metrics."""
        metrics = DashboardMetrics.objects.create(
            date=timezone.now().date(),
            campaign=self.campaign,
            active_campaigns=5,
            high_echo_communities=3,
            positivity_ratio=0.65,
            llm_tokens_used=50000,
            llm_cost_usd=5.50
        )

        serializer = DashboardMetricsSerializer(metrics)
        data = serializer.data

        self.assertEqual(data['active_campaigns'], 5)
        self.assertEqual(data['high_echo_communities'], 3)
        self.assertEqual(float(data['positivity_ratio']), 0.65)
        self.assertEqual(data['llm_tokens_used'], 50000)
        self.assertEqual(data['campaign_name'], 'Test Campaign')

    def test_dashboard_metrics_deserialization(self):
        """Test deserializing dashboard metrics data."""
        data = {
            'date': timezone.now().date(),
            'campaign': self.campaign.id,
            'active_campaigns': 10,
            'high_echo_communities': 5,
            'positivity_ratio': 0.70
        }

        serializer = DashboardMetricsSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        metrics = serializer.save()
        self.assertEqual(metrics.active_campaigns, 10)
        self.assertEqual(metrics.high_echo_communities, 5)

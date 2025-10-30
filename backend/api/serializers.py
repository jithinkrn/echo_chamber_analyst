"""
API serializers for EchoChamber Analyst admin functionality.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from common.models import (
    Brand, Competitor, Campaign, Source, RawContent, ProcessedContent,
    Insight, Influencer, AuditLog, AgentMetrics,
    Community, PainPoint, Thread, DashboardMetrics
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                 'is_staff', 'is_superuser', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for Brand model."""

    competitors = serializers.SerializerMethodField()
    campaign_count = serializers.SerializerMethodField()
    has_active_auto_campaign = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_competitors(self, obj):
        """Get competitors for this brand."""
        return CompetitorSerializer(obj.competitors.filter(is_active=True), many=True).data

    def get_campaign_count(self, obj):
        """Get active campaign count for this brand."""
        return obj.campaigns.filter(status='active').count()

    def get_has_active_auto_campaign(self, obj):
        """Check if brand has an active automatic campaign."""
        return obj.campaigns.filter(
            metadata__is_auto_campaign=True,
            status__in=['active', 'paused']
        ).exists()


class CompetitorSerializer(serializers.ModelSerializer):
    """Serializer for Competitor model."""

    brand_name = serializers.CharField(source='brand.name', read_only=True)

    class Meta:
        model = Competitor
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model."""

    owner_name = serializers.CharField(source='owner.username', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)

    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_spend', 'last_run_at']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class SourceSerializer(serializers.ModelSerializer):
    """Serializer for Source model."""

    class Meta:
        model = Source
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_accessed']


class RawContentSerializer(serializers.ModelSerializer):
    """Serializer for RawContent model."""

    source_name = serializers.CharField(source='source.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        model = RawContent
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProcessedContentSerializer(serializers.ModelSerializer):
    """Serializer for ProcessedContent model."""

    raw_content_title = serializers.CharField(source='raw_content.title', read_only=True)

    class Meta:
        model = ProcessedContent
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InsightSerializer(serializers.ModelSerializer):
    """Serializer for Insight model."""

    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    content_count = serializers.SerializerMethodField()

    class Meta:
        model = Insight
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_content_count(self, obj):
        return obj.content.count()


class InfluencerSerializer(serializers.ModelSerializer):
    """Serializer for Influencer model."""

    campaign_name = serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        model = Influencer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    user_name = serializers.CharField(source='user.username', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentMetricsSerializer(serializers.ModelSerializer):
    """Serializer for AgentMetrics model."""

    campaign_name = serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        model = AgentMetrics
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# Summary/Statistics Serializers

class CampaignSummarySerializer(serializers.Serializer):
    """Serializer for campaign summary statistics."""

    campaign = CampaignSerializer()
    total_content = serializers.IntegerField()
    processed_content = serializers.IntegerField()
    total_insights = serializers.IntegerField()
    validated_insights = serializers.IntegerField()
    total_influencers = serializers.IntegerField()
    current_spend = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_activity = serializers.DateTimeField()


class SystemStatsSerializer(serializers.Serializer):
    """Serializer for system-wide statistics."""

    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    total_content = serializers.IntegerField()
    total_insights = serializers.IntegerField()
    total_users = serializers.IntegerField()
    agents_status = serializers.DictField()
    daily_costs = serializers.DecimalField(max_digits=10, decimal_places=2)
    api_requests_today = serializers.IntegerField()


class AgentStatusSerializer(serializers.Serializer):
    """Serializer for agent health status."""

    agent_name = serializers.CharField()
    status = serializers.CharField()
    last_seen = serializers.DateTimeField()
    capabilities = serializers.ListField()
    current_tasks = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_response_time = serializers.FloatField()


# Dashboard Serializers

class DashboardKPISerializer(serializers.Serializer):
    """Serializer for dashboard KPI metrics."""
    
    active_campaigns = serializers.IntegerField()
    high_echo_communities = serializers.IntegerField()
    high_echo_change_percent = serializers.FloatField()
    new_pain_points_above_50 = serializers.IntegerField()
    new_pain_points_change = serializers.IntegerField()
    positivity_ratio = serializers.FloatField()
    positivity_change_pp = serializers.FloatField()
    llm_tokens_used = serializers.IntegerField()
    llm_cost_usd = serializers.FloatField()


class CommunitySerializer(serializers.ModelSerializer):
    """Serializer for Community model."""
    
    class Meta:
        model = Community
        fields = '__all__'
        read_only_fields = ['id', 'last_analyzed']


class PainPointSerializer(serializers.ModelSerializer):
    """Serializer for PainPoint model."""
    
    community_name = serializers.CharField(source='community.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = PainPoint
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class CommunityHeatMapSerializer(serializers.ModelSerializer):
    """Serializer for community heatmap data."""
    
    pain_points = serializers.SerializerMethodField()
    
    class Meta:
        model = Community
        fields = ['name', 'platform', 'echo_score', 'echo_score_change', 'pain_points']
    
    def get_pain_points(self, obj):
        from datetime import datetime, timedelta
        pain_points = PainPoint.objects.filter(
            community=obj,
            created_at__gte=datetime.now() - timedelta(days=7)
        ).order_by('-growth_percentage')[:3]
        
        return [{
            'keyword': pp.keyword,
            'growth_percentage': pp.growth_percentage,
            'heat_level': pp.heat_level
        } for pp in pain_points]


class TopPainPointSerializer(serializers.ModelSerializer):
    """Serializer for top pain points."""
    
    class Meta:
        model = PainPoint
        fields = ['keyword', 'growth_percentage', 'mention_count']


class InfluencerPulseSerializer(serializers.ModelSerializer):
    """Serializer for influencer pulse data."""
    
    topics_text = serializers.SerializerMethodField()
    
    class Meta:
        model = Influencer
        fields = ['handle', 'platform', 'reach', 'engagement_rate', 'topics_text']
    
    def get_topics_text(self, obj):
        return ', '.join(obj.topics[:3]) if obj.topics else ''


class ThreadSerializer(serializers.ModelSerializer):
    """Serializer for Thread model."""
    
    community_name = serializers.CharField(source='community.name', read_only=True)
    community_platform = serializers.CharField(source='community.platform', read_only=True)
    pain_point_chips = serializers.SerializerMethodField()
    influencer_mentions = serializers.SerializerMethodField()
    
    class Meta:
        model = Thread
        fields = '__all__'
        read_only_fields = ['id', 'analyzed_at']
    
    def get_pain_point_chips(self, obj):
        return [pp.keyword for pp in obj.pain_points.all()]
    
    def get_influencer_mentions(self, obj):
        return [{
            'handle': inf.handle,
            'karma_score': inf.karma_score
        } for inf in obj.influencers_mentioned.all()]


class CommunityWatchlistSerializer(serializers.Serializer):
    """Serializer for community watchlist data."""
    
    rank = serializers.IntegerField()
    name = serializers.CharField()
    echo_score = serializers.FloatField()
    echo_change = serializers.FloatField()
    new_threads = serializers.IntegerField()
    key_influencer = serializers.CharField()


class DashboardMetricsSerializer(serializers.ModelSerializer):
    """Serializer for DashboardMetrics model."""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = DashboardMetrics
        fields = '__all__'
        read_only_fields = ['id']
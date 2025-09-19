"""
API serializers for EchoChamber Analyst admin functionality.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from common.models import (
    Campaign, Source, RawContent, ProcessedContent,
    Insight, Influencer, AuditLog, AgentMetrics
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                 'is_staff', 'is_superuser', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model."""

    owner_name = serializers.CharField(source='owner.username', read_only=True)

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
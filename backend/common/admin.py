"""
Admin configuration for common models.
"""

from django.contrib import admin
from .models import (
    Campaign, Source, RawContent, ProcessedContent,
    Insight, Influencer, AuditLog, AgentMetrics
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'status', 'created_at', 'last_run_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'url', 'is_active', 'rate_limit']
    list_filter = ['source_type', 'is_active']
    search_fields = ['name', 'url']


@admin.register(RawContent)
class RawContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'campaign', 'published_at', 'is_processed', 'echo_score']
    list_filter = ['source', 'campaign', 'is_processed', 'published_at']
    search_fields = ['title', 'content', 'author']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ProcessedContent)
class ProcessedContentAdmin(admin.ModelAdmin):
    list_display = ['raw_content', 'language', 'sentiment_score', 'toxicity_score', 'spam_score']
    list_filter = ['language', 'processing_version']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'insight_type', 'campaign', 'confidence_score', 'priority_score', 'is_validated']
    list_filter = ['insight_type', 'campaign', 'is_validated']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Influencer)
class InfluencerAdmin(admin.ModelAdmin):
    list_display = ['username', 'display_name', 'source_type', 'campaign', 'influence_score']
    list_filter = ['source_type', 'campaign']
    search_fields = ['username', 'display_name']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'user', 'campaign', 'agent_name', 'created_at', 'execution_time']
    list_filter = ['action_type', 'agent_name', 'created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    search_fields = ['action_description', 'agent_name']


@admin.register(AgentMetrics)
class AgentMetricsAdmin(admin.ModelAdmin):
    list_display = ['agent_name', 'campaign', 'metric_date', 'success_rate', 'execution_time', 'cost']
    list_filter = ['agent_name', 'metric_date', 'campaign']
    readonly_fields = ['id', 'created_at', 'updated_at']
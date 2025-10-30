"""
Core models for EchoChamber Analyst.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from pgvector.django import VectorField
import uuid
import json


class BaseModel(models.Model):
    """Base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Brand(BaseModel):
    """Brand/Company being analyzed for echo chamber effects."""
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    # Brand details
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    
    # Social media handles (optional)
    social_handles = models.JSONField(default=dict)  # {"twitter": "@brand", "instagram": "@brand"}
    
    # Monitoring configuration
    primary_keywords = models.JSONField(default=list)  # Main brand keywords
    product_keywords = models.JSONField(default=list)  # Product-specific keywords
    exclude_keywords = models.JSONField(default=list)  # Keywords to exclude
    
    # Sources to monitor for this brand
    sources = models.JSONField(default=list)  # Reddit subreddits, Discord servers, etc.
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'brands'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Competitor(BaseModel):
    """Competitor of a brand for competitive analysis."""
    
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='competitors')
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    
    # Competitive monitoring
    keywords = models.JSONField(default=list)
    social_handles = models.JSONField(default=dict)
    
    # Competitive metrics
    market_share_estimate = models.FloatField(null=True, blank=True)  # Percentage
    sentiment_comparison = models.FloatField(null=True, blank=True)  # vs brand sentiment
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'competitors'
        ordering = ['name']
        unique_together = ['brand', 'name']
    
    def __str__(self):
        return f"{self.name} (competitor of {self.brand.name})"


class Campaign(BaseModel):
    """Marketing campaign for tracking conversations."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='campaigns', null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Target configuration
    keywords = models.JSONField(default=list)  # Keywords to search for
    sources = models.JSONField(default=list)  # Reddit subreddits, Discord servers, etc.
    exclude_keywords = models.JSONField(default=list)  # Keywords to exclude

    # Scheduling
    schedule_enabled = models.BooleanField(default=True)
    schedule_interval = models.IntegerField(default=3600)  # Seconds between runs
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    # Campaign duration
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Budget and limits
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    current_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Total budget limit

    # Analysis metadata - stores comprehensive analysis summaries
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Source(BaseModel):
    """Data source (Reddit, Discord, forums, etc.)."""

    SOURCE_TYPES = [
        ('reddit', 'Reddit'),
        ('discord', 'Discord'),
        ('forum', 'Forum'),
        ('website', 'Website'),
    ]

    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    url = models.URLField()
    description = models.TextField(blank=True)  # Source description

    # Configuration
    config = models.JSONField(default=dict)  # Source-specific configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)  # Whether this is a default source
    category = models.CharField(max_length=50, blank=True)  # fashion, technology, reviews, etc.

    # Rate limiting
    rate_limit = models.IntegerField(default=60)  # Requests per minute
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sources'
        unique_together = ['source_type', 'url']

    def __str__(self):
        return f"{self.name} ({self.source_type})"


class RawContent(BaseModel):
    """Raw content scraped from sources."""

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='raw_content')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='raw_content')

    # Content metadata
    external_id = models.CharField(max_length=255)  # Original ID from source
    url = models.URLField()
    title = models.CharField(max_length=500, blank=True)
    author = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField()

    # Content
    content = models.TextField()
    metadata = models.JSONField(default=dict)  # Additional metadata

    # Processing status
    is_processed = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)

    # EchoScore components
    echo_score = models.FloatField(null=True, blank=True)
    depth_score = models.FloatField(null=True, blank=True)
    diversity_score = models.FloatField(null=True, blank=True)
    recency_score = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'raw_content'
        unique_together = ['source', 'external_id']
        ordering = ['-published_at']

    def __str__(self):
        return f"{self.title[:50]}..." if self.title else f"Content {self.external_id}"


class ProcessedContent(BaseModel):
    """Cleaned and processed content."""

    raw_content = models.OneToOneField(RawContent, on_delete=models.CASCADE, related_name='processed')

    # Cleaned content
    cleaned_content = models.TextField()
    language = models.CharField(max_length=10, default='en')

    # Content analysis
    sentiment_score = models.FloatField(null=True, blank=True)  # -1 to 1
    toxicity_score = models.FloatField(null=True, blank=True)   # 0 to 1
    spam_score = models.FloatField(null=True, blank=True)       # 0 to 1

    # Extracted entities
    keywords = models.JSONField(default=list)
    entities = models.JSONField(default=dict)
    topics = models.JSONField(default=list)

    # Processing metadata
    processing_version = models.CharField(max_length=50, default='1.0')
    processing_time = models.DurationField(null=True, blank=True)

    # Vector embedding for semantic search
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, default='text-embedding-3-small')
    embedding_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'processed_content'

    def __str__(self):
        return f"Processed: {self.raw_content}"


class Insight(BaseModel):
    """Generated insights from content analysis."""

    INSIGHT_TYPES = [
        ('pain_point', 'Pain Point'),
        ('praise', 'Praise'),
        ('feature_request', 'Feature Request'),
        ('competitor_mention', 'Competitor Mention'),
        ('trend', 'Trend'),
        ('influencer', 'Influencer'),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='insights')
    content = models.ManyToManyField(ProcessedContent, related_name='insights')

    # Insight details
    insight_type = models.CharField(max_length=30, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    summary = models.TextField(blank=True)

    # Scoring
    confidence_score = models.FloatField()  # 0 to 1
    impact_score = models.FloatField(null=True, blank=True)  # 0 to 1
    priority_score = models.FloatField(null=True, blank=True)  # 0 to 1

    # Metadata
    tags = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)

    # User feedback
    is_validated = models.BooleanField(default=False)
    user_rating = models.IntegerField(null=True, blank=True)  # 1-5 stars
    user_feedback = models.TextField(blank=True)

    # Vector embedding for semantic search
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, default='text-embedding-3-small')
    embedding_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'insights'
        ordering = ['-priority_score', '-confidence_score']

    def __str__(self):
        return self.title


class Influencer(BaseModel):
    """Identified influencers from content analysis."""

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='influencers')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='influencers', null=True, blank=True)
    community = models.ForeignKey('Community', on_delete=models.CASCADE, related_name='influencers', null=True, blank=True)

    # Influencer details
    username = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=20)
    profile_url = models.URLField(blank=True)
    platform = models.CharField(max_length=50, default='reddit')  # reddit, discord, forum

    # Engagement metrics (from Reddit/forum data)
    total_karma = models.IntegerField(default=0)
    total_posts = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    avg_post_score = models.FloatField(default=0.0)
    avg_engagement_rate = models.FloatField(default=0.0)

    # Influence component scores (0-100 scale)
    reach_score = models.FloatField(default=0.0)  # Estimated audience size
    authority_score = models.FloatField(default=0.0)  # Domain expertise
    advocacy_score = models.FloatField(default=0.0)  # Brand promotion level
    relevance_score = models.FloatField(default=0.0)  # Brand/topic relevance

    # Overall influence score (weighted combination)
    influence_score = models.FloatField(default=0.0)  # 0 to 100

    # Brand sentiment
    sentiment_towards_brand = models.FloatField(default=0.0)  # -1 to +1
    brand_mention_count = models.IntegerField(default=0)
    brand_mention_rate = models.FloatField(default=0.0)  # Percentage of posts mentioning brand

    # Activity patterns
    communities = models.JSONField(default=list)  # List of subreddits/channels
    first_seen = models.DateTimeField(default=timezone.now)
    last_active = models.DateTimeField(null=True, blank=True)
    post_frequency = models.FloatField(default=0.0)  # posts per week

    # Legacy metrics (for backward compatibility)
    reach = models.IntegerField(default=0)  # follower count
    engagement_rate = models.FloatField(default=0.0)
    karma_score = models.IntegerField(default=0)
    topics = models.JSONField(default=list)  # topics they talk about
    follower_count = models.IntegerField(null=True, blank=True)
    avg_likes = models.FloatField(null=True, blank=True)
    avg_comments = models.FloatField(null=True, blank=True)
    content_topics = models.JSONField(default=list)
    sentiment_distribution = models.JSONField(default=dict)

    # Sample threads for reference
    sample_thread_ids = models.JSONField(default=list)  # Store up to 5 thread IDs

    class Meta:
        db_table = 'influencers'
        unique_together = ['campaign', 'username', 'source_type']
        ordering = ['-influence_score']
        indexes = [
            models.Index(fields=['brand', '-relevance_score']),
            models.Index(fields=['campaign', '-influence_score']),
            models.Index(fields=['platform', '-reach_score']),
        ]

    def __str__(self):
        return f"{self.display_name or self.username} ({self.source_type})"


class AuditLog(BaseModel):
    """Audit trail for all system actions."""

    ACTION_TYPES = [
        ('campaign_created', 'Campaign Created'),
        ('campaign_updated', 'Campaign Updated'),
        ('content_scraped', 'Content Scraped'),
        ('content_processed', 'Content Processed'),
        ('insight_generated', 'Insight Generated'),
        ('user_action', 'User Action'),
        ('agent_action', 'Agent Action'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True)

    # Action details
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    action_description = models.TextField()

    # Technical details
    agent_name = models.CharField(max_length=100, blank=True)
    model_version = models.CharField(max_length=50, blank=True)
    prompt_hash = models.CharField(max_length=64, blank=True)  # SHA-256 of prompt

    # Performance metrics
    execution_time = models.DurationField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Additional data
    metadata = models.JSONField(default=dict)
    error_details = models.TextField(blank=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action_type} at {self.created_at}"


class AgentMetrics(BaseModel):
    """Performance metrics for agents."""

    agent_name = models.CharField(max_length=100)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True)

    # Performance metrics
    execution_time = models.DurationField()
    success_rate = models.FloatField()  # 0 to 1
    error_count = models.IntegerField(default=0)

    # Resource usage
    cpu_usage = models.FloatField(null=True, blank=True)
    memory_usage = models.FloatField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Quality metrics
    accuracy_score = models.FloatField(null=True, blank=True)
    precision_score = models.FloatField(null=True, blank=True)
    recall_score = models.FloatField(null=True, blank=True)

    # Timestamp for metrics collection
    metric_date = models.DateField(default=timezone.now)

    class Meta:
        db_table = 'agent_metrics'
        unique_together = ['agent_name', 'metric_date', 'campaign']
        ordering = ['-metric_date']

    def __str__(self):
        return f"{self.agent_name} metrics for {self.metric_date}"


class Community(BaseModel):
    """Online communities tracked for conversations."""
    
    PLATFORM_CHOICES = [
        ('reddit', 'Reddit'),
        ('discord', 'Discord'),
        ('tiktok', 'TikTok'),
        ('forum', 'Forum'),
        ('twitter', 'Twitter'),
    ]
    
    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField()
    member_count = models.IntegerField(default=0)
    echo_score = models.FloatField(default=0.0)
    echo_score_change = models.FloatField(default=0.0)  # percentage change
    is_active = models.BooleanField(default=True)
    last_analyzed = models.DateTimeField(auto_now=True)
    
    # Community metadata
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=10, default='en')
    
    class Meta:
        db_table = 'communities'
        verbose_name_plural = "Communities"
        unique_together = ['platform', 'name']
        ordering = ['-echo_score']
    
    def __str__(self):
        return f"{self.name} ({self.platform})"


class PainPoint(BaseModel):
    """Pain points extracted from content analysis."""
    
    keyword = models.CharField(max_length=100)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='pain_points')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='pain_points')
    
    # Metrics
    mention_count = models.IntegerField(default=0)
    growth_percentage = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(default=0.0)
    heat_level = models.IntegerField(default=1)  # 1-5 for heat map visualization
    
    # Context
    example_content = models.TextField(blank=True)
    related_keywords = models.JSONField(default=list)
    
    # Time tracking
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    # Vector embedding for semantic search
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, default='text-embedding-3-small')
    embedding_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pain_points'
        unique_together = ['keyword', 'campaign', 'community']
        ordering = ['-growth_percentage', '-mention_count']
    
    def __str__(self):
        return f"{self.keyword} (+{self.growth_percentage}%)"


class Thread(BaseModel):
    """Individual threads/posts from communities."""
    
    thread_id = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    content = models.TextField()
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='threads')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='threads')
    
    # Thread metadata
    author = models.CharField(max_length=100)
    author_karma = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    
    # Analysis results
    echo_score = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(default=0.0)
    pain_points = models.ManyToManyField(PainPoint, blank=True)
    influencers_mentioned = models.ManyToManyField(Influencer, blank=True)
    
    # LLM processing
    llm_summary = models.TextField(blank=True)
    token_count = models.IntegerField(default=0)
    processing_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0.0)
    
    # Timestamps
    published_at = models.DateTimeField()
    analyzed_at = models.DateTimeField(auto_now=True)
    
    # Engagement metrics
    engagement_rate = models.FloatField(default=0.0)
    controversy_score = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'threads'
        unique_together = ['thread_id', 'community']
        ordering = ['-published_at']
    
    def __str__(self):
        return f"{self.title[:50]}..." if self.title else f"Thread {self.thread_id}"


class DashboardMetrics(BaseModel):
    """Daily aggregated metrics for dashboard KPIs."""
    
    date = models.DateField()
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='dashboard_metrics')
    
    # KPI Metrics
    active_campaigns = models.IntegerField(default=0)
    high_echo_communities = models.IntegerField(default=0)
    high_echo_change_percent = models.FloatField(default=0.0)
    new_pain_points_above_50 = models.IntegerField(default=0)
    new_pain_points_change = models.IntegerField(default=0)
    positivity_ratio = models.FloatField(default=0.0)
    positivity_change_pp = models.FloatField(default=0.0)  # percentage points
    llm_tokens_used = models.IntegerField(default=0)
    llm_cost_usd = models.FloatField(default=0.0)
    
    # Content metrics
    total_threads_analyzed = models.IntegerField(default=0)
    total_communities_tracked = models.IntegerField(default=0)
    total_influencers_identified = models.IntegerField(default=0)
    
    # Quality metrics
    sentiment_average = models.FloatField(default=0.0)
    echo_score_average = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'dashboard_metrics'
        unique_together = ['date', 'campaign']
        ordering = ['-date']
    
    def __str__(self):
        return f"Dashboard metrics for {self.campaign.name} on {self.date}"
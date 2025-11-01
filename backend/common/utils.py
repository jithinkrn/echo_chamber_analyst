"""
Utility functions for Common app
"""
from django.db.models import Sum, Count
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_community_echo_score(community_id: int, months: int = 6) -> float:
    """
    Calculate echo score (0-100) for a community based on actual collected data.
    
    Formula:
    - Thread Volume (40%): How many threads mention the brand
    - Pain Point Intensity (30%): How many unique pain points discussed
    - Engagement Depth (30%): Total comments/upvotes across threads
    
    Args:
        community_id: ID of the community
        months: Number of months to analyze (default 6)
        
    Returns:
        float: Echo score between 0 and 100
    """
    from common.models import Community, Thread, PainPoint
    
    try:
        community = Community.objects.get(id=community_id)
    except Community.DoesNotExist:
        logger.error(f"Community {community_id} not found")
        return 0.0
    
    # Get data for this community
    threads = Thread.objects.filter(community=community)
    pain_points = PainPoint.objects.filter(community=community)
    
    # 1. Thread Volume Score (0-40 points)
    # 20+ threads = max 40 points
    thread_count = threads.count()
    thread_score = min(40, thread_count * 2)
    
    # 2. Pain Point Intensity Score (0-30 points)
    # 10+ unique pain points = max 30 points
    unique_pain_points = pain_points.values('keyword').distinct().count()
    pain_point_score = min(30, unique_pain_points * 3)
    
    # 3. Engagement Depth Score (0-30 points)
    # 600+ total engagement = max 30 points
    engagement_data = threads.aggregate(
        total_upvotes=Sum('upvotes'),
        total_comments=Sum('comment_count')
    )
    
    upvotes = engagement_data['total_upvotes'] or 0
    comments = engagement_data['total_comments'] or 0
    total_engagement = upvotes + comments
    engagement_score = min(30, total_engagement / 20)
    
    # Calculate total echo score
    echo_score = round(thread_score + pain_point_score + engagement_score, 1)
    
    logger.debug(f"Community {community.name}: threads={thread_count}, pain_points={unique_pain_points}, "
                f"engagement={total_engagement} → score={echo_score}")
    
    return echo_score


def recalculate_all_community_scores(campaign_id: Optional[int] = None):
    """
    Recalculate echo scores for all communities.
    
    Args:
        campaign_id: If provided, only recalculate for this campaign
    """
    from common.models import Community
    
    communities = Community.objects.all()
    if campaign_id:
        communities = communities.filter(campaign_id=campaign_id)
    
    updated_count = 0
    for community in communities:
        new_score = calculate_community_echo_score(community.id)
        if community.echo_score != new_score:
            community.echo_score = new_score
            community.save(update_fields=['echo_score'])
            updated_count += 1
    
    logger.info(f"Recalculated echo scores for {updated_count} communities")
    return updated_count

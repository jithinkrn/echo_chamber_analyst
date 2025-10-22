"""
Analyst Agent - Unified Content & Influencer Analysis

This module consolidates all analysis capabilities into a single Analyst Agent:
- Content analysis and insight generation
- Influencer identification and scoring
- Pain point to influencer linking
- Comprehensive summaries with impact metrics
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from django.db.models import Avg, Count, Sum, Q
from common.models import Thread, Influencer, Brand, Campaign, Community, PainPoint

logger = logging.getLogger(__name__)


# ============================================================================
# INFLUENCER ANALYSIS FUNCTIONS
# ============================================================================

def analyze_influencers_for_threads(
    threads: List[Thread],
    brand: Brand,
    campaign: Campaign,
    min_posts: int = 2
) -> Tuple[List[Dict], Dict[str, List[str]]]:
    """
    Analyze threads to identify and rank influencers.

    Returns:
        Tuple of (influencer_list, influencer_threads_map)
        - influencer_list: List of influencer data dicts
        - influencer_threads_map: Map of username -> list of thread_ids
    """
    logger.info(f"Analyzing {len(threads)} threads for influencers")

    if not threads:
        return [], {}

    # Aggregate user metrics from threads
    user_metrics = aggregate_user_metrics_from_threads(threads, brand)

    # Filter users with minimum activity
    active_users = {
        username: metrics
        for username, metrics in user_metrics.items()
        if metrics.get('total_posts', 0) >= min_posts
    }

    logger.info(f"Found {len(active_users)} active users (min {min_posts} posts)")

    # Calculate influence scores for each user
    influencers = []
    influencer_threads_map = {}

    for username, metrics in active_users.items():
        scores = calculate_influence_scores(username, metrics, brand)

        influencer_data = {
            'username': username,
            'display_name': metrics.get('display_name', username),
            'platform': metrics.get('platform', 'reddit'),
            'profile_url': metrics.get('profile_url', ''),
            'total_posts': metrics['total_posts'],
            'total_comments': metrics.get('total_comments', 0),
            'total_karma': metrics.get('total_karma', 0),
            'avg_post_score': metrics.get('avg_post_score', 0.0),
            'avg_engagement_rate': metrics.get('avg_engagement_rate', 0.0),
            'reach_score': scores['reach_score'],
            'authority_score': scores['authority_score'],
            'advocacy_score': scores['advocacy_score'],
            'relevance_score': scores['relevance_score'],
            'influence_score': scores['influence_score'],
            'sentiment_towards_brand': metrics.get('brand_sentiment', 0.0),
            'brand_mention_count': metrics.get('brand_mentions', 0),
            'brand_mention_rate': (metrics.get('brand_mentions', 0) / max(metrics['total_posts'], 1)) * 100,
            'communities': list(metrics.get('communities', set())),
            'sample_thread_ids': metrics.get('thread_ids', [])[:10]
        }

        influencers.append(influencer_data)
        influencer_threads_map[username] = metrics.get('thread_ids', [])

    # Sort by influence score
    influencers.sort(key=lambda x: x['influence_score'], reverse=True)

    logger.info(f"Identified {len(influencers)} influencers")
    return influencers, influencer_threads_map


def aggregate_user_metrics_from_threads(threads: List[Thread], brand: Brand) -> Dict[str, Dict]:
    """Aggregate metrics for users across all threads."""
    user_metrics = defaultdict(lambda: {
        'total_posts': 0,
        'total_comments': 0,
        'total_karma': 0,
        'total_engagement': 0,
        'brand_mentions': 0,
        'brand_sentiment': 0.0,
        'communities': set(),
        'thread_ids': [],
        'platform': 'reddit'
    })

    for thread in threads:
        if not hasattr(thread, 'author_username') or not thread.author_username:
            continue

        username = thread.author_username
        metrics = user_metrics[username]

        metrics['total_posts'] += 1
        metrics['total_karma'] += getattr(thread, 'upvotes', 0) - getattr(thread, 'downvotes', 0)
        metrics['total_engagement'] += getattr(thread, 'comment_count', 0)
        metrics['thread_ids'].append(str(thread.id))

        if thread.community:
            metrics['communities'].add(thread.community.name)
            metrics['platform'] = getattr(thread.community, 'platform', 'reddit')

        # Check for brand mentions
        content_lower = (thread.title + ' ' + thread.content).lower()
        brand_keywords = [brand.name.lower()] + [kw.lower() for kw in brand.primary_keywords]

        if any(keyword in content_lower for keyword in brand_keywords):
            metrics['brand_mentions'] += 1
            if hasattr(thread, 'sentiment_score'):
                metrics['brand_sentiment'] += thread.sentiment_score

    # Calculate averages
    for username, metrics in user_metrics.items():
        if metrics['brand_mentions'] > 0:
            metrics['brand_sentiment'] /= metrics['brand_mentions']

        metrics['avg_post_score'] = metrics['total_karma'] / max(metrics['total_posts'], 1)
        metrics['avg_engagement_rate'] = metrics['total_engagement'] / max(metrics['total_posts'], 1)
        metrics['communities'] = list(metrics['communities'])

    return dict(user_metrics)


def calculate_influence_scores(username: str, metrics: Dict, brand: Brand) -> Dict:
    """
    Calculate multi-dimensional influence scores.

    Returns dict with: reach_score, authority_score, advocacy_score, relevance_score, influence_score
    """
    reach_score = calculate_reach_score(metrics)
    authority_score = calculate_authority_score(metrics)
    advocacy_score = calculate_advocacy_score(metrics, brand)
    relevance_score = calculate_relevance_score(metrics, brand)

    # Weighted overall score
    influence_score = (
        reach_score * 0.30 +
        authority_score * 0.30 +
        advocacy_score * 0.20 +
        relevance_score * 0.20
    )

    return {
        'reach_score': round(reach_score, 2),
        'authority_score': round(authority_score, 2),
        'advocacy_score': round(advocacy_score, 2),
        'relevance_score': round(relevance_score, 2),
        'influence_score': round(influence_score, 2)
    }


def calculate_reach_score(metrics: Dict) -> float:
    """Calculate reach score (0-100) based on audience size metrics."""
    total_posts = metrics.get('total_posts', 0)
    total_engagement = metrics.get('total_engagement', 0)
    communities = metrics.get('communities', [])

    # Post volume score (max 40 points)
    post_score = min(total_posts / 100, 1.0) * 40

    # Engagement score (max 40 points)
    engagement_score = min(total_engagement / 1000, 1.0) * 40

    # Community diversity score (max 20 points)
    diversity_score = min(len(communities) / 5, 1.0) * 20

    return post_score + engagement_score + diversity_score


def calculate_authority_score(metrics: Dict) -> float:
    """Calculate authority score (0-100) based on credibility metrics."""
    total_posts = metrics.get('total_posts', 0)
    avg_post_score = metrics.get('avg_post_score', 0)
    avg_engagement = metrics.get('avg_engagement_rate', 0)

    # Consistency score (max 40 points)
    consistency_score = min(total_posts / 50, 1.0) * 40

    # Quality score (max 30 points)
    quality_score = min(max(avg_post_score, 0) / 100, 1.0) * 30

    # Engagement ratio score (max 30 points)
    engagement_ratio_score = min(avg_engagement / 10, 1.0) * 30

    return consistency_score + quality_score + engagement_ratio_score


def calculate_advocacy_score(metrics: Dict, brand: Brand) -> float:
    """Calculate advocacy score (0-100) based on brand promotion."""
    total_posts = metrics.get('total_posts', 0)
    brand_mentions = metrics.get('brand_mentions', 0)
    brand_sentiment = metrics.get('brand_sentiment', 0.0)

    if total_posts == 0:
        return 0.0

    # Mention rate score (60% weight)
    mention_rate = (brand_mentions / total_posts) * 100
    mention_score = min(mention_rate / 20, 1.0) * 60  # 20% mention rate = max

    # Sentiment score (40% weight)
    # Convert sentiment from -1..1 to 0..100
    sentiment_normalized = ((brand_sentiment + 1) / 2) * 100
    sentiment_score = (sentiment_normalized / 100) * 40

    return mention_score + sentiment_score


def calculate_relevance_score(metrics: Dict, brand: Brand) -> float:
    """Calculate relevance score (0-100) based on topic alignment."""
    brand_mentions = metrics.get('brand_mentions', 0)
    total_posts = metrics.get('total_posts', 0)
    communities = metrics.get('communities', [])

    # Mention frequency score (max 50 points)
    mention_score = min(brand_mentions / 10, 1.0) * 50

    # Post volume score (max 30 points)
    volume_score = min(total_posts / 50, 1.0) * 30

    # Community relevance score (max 20 points)
    # Check if user is active in brand-related communities
    relevant_communities = len([c for c in communities if any(
        keyword.lower() in c.lower()
        for keyword in [brand.name] + brand.primary_keywords
    )])
    community_score = min(relevant_communities / 3, 1.0) * 20

    return mention_score + volume_score + community_score


def save_influencers_to_db(
    brand: Brand,
    campaign: Campaign,
    influencers: List[Dict]
) -> List[Influencer]:
    """Save influencers to database."""
    saved_influencers = []

    for inf_data in influencers:
        influencer, created = Influencer.objects.update_or_create(
            campaign=campaign,
            username=inf_data['username'],
            platform=inf_data.get('platform', 'reddit'),
            defaults={
                'brand': brand,
                'display_name': inf_data.get('display_name', ''),
                'profile_url': inf_data.get('profile_url', ''),
                'total_posts': inf_data.get('total_posts', 0),
                'total_comments': inf_data.get('total_comments', 0),
                'total_karma': inf_data.get('total_karma', 0),
                'avg_post_score': inf_data.get('avg_post_score', 0.0),
                'avg_engagement_rate': inf_data.get('avg_engagement_rate', 0.0),
                'reach_score': inf_data.get('reach_score', 0.0),
                'authority_score': inf_data.get('authority_score', 0.0),
                'advocacy_score': inf_data.get('advocacy_score', 0.0),
                'relevance_score': inf_data.get('relevance_score', 0.0),
                'influence_score': inf_data.get('influence_score', 0.0),
                'sentiment_towards_brand': inf_data.get('sentiment_towards_brand', 0.0),
                'brand_mention_count': inf_data.get('brand_mention_count', 0),
                'brand_mention_rate': inf_data.get('brand_mention_rate', 0.0),
                'communities': inf_data.get('communities', []),
                'sample_thread_ids': inf_data.get('sample_thread_ids', [])
            }
        )
        saved_influencers.append(influencer)

    logger.info(f"Saved {len(saved_influencers)} influencers to database")
    return saved_influencers


# ============================================================================
# PAIN POINT TO INFLUENCER LINKING
# ============================================================================

def link_pain_points_to_influencers(
    pain_points: List[PainPoint],
    influencers: List[Dict],
    influencer_threads_map: Dict[str, List[str]]
) -> Dict[str, Dict]:
    """
    Link pain points to influencers who discussed them.

    Returns: Dict mapping pain point keywords to analysis data
    """
    logger.info(f"Linking {len(pain_points)} pain points to {len(influencers)} influencers")

    pain_point_analysis = {}

    for pp in pain_points:
        # Get threads associated with this pain point
        thread_ids = set(str(t.id) for t in pp.threads.all())

        # Find influencers who participated in these threads
        relevant_influencers = []
        total_reach = 0
        sentiment_breakdown = {'positive': 0, 'negative': 0, 'neutral': 0}

        for inf in influencers:
            username = inf['username']
            inf_threads = set(influencer_threads_map.get(username, []))

            # Check if influencer participated in pain point threads
            if thread_ids & inf_threads:
                relevant_influencers.append(inf)
                total_reach += inf.get('total_karma', 0)  # Using karma as proxy for reach

                # Categorize sentiment
                sentiment = inf.get('sentiment_towards_brand', 0.0)
                if sentiment > 0.2:
                    sentiment_breakdown['positive'] += 1
                elif sentiment < -0.2:
                    sentiment_breakdown['negative'] += 1
                else:
                    sentiment_breakdown['neutral'] += 1

        # Calculate urgency score
        frequency = len(thread_ids)
        influencer_count = len(relevant_influencers)

        # Urgency: 0-10 scale based on frequency and influencer involvement
        urgency_score = min(
            (frequency / 5) * 5 +  # Frequency component (max 5 points)
            (influencer_count / 10) * 5,  # Influencer component (max 5 points)
            10
        )

        # Generate recommendation
        if urgency_score >= 8:
            recommendation = "CRITICAL: Immediate executive response required. High-influence users are actively discussing this issue."
        elif urgency_score >= 5:
            recommendation = "HIGH: Engage high-influence advocates/critics promptly. Prepare targeted response."
        else:
            recommendation = "MONITOR: Track sentiment trends. Potential future concern."

        pain_point_analysis[pp.keyword] = {
            'pain_point': pp.keyword,
            'urgency_score': round(urgency_score, 1),
            'frequency': frequency,
            'influencer_count': influencer_count,
            'estimated_reach': total_reach,
            'sentiment_breakdown': sentiment_breakdown,
            'recommended_action': recommendation,
            'top_influencers': sorted(
                relevant_influencers,
                key=lambda x: x['influence_score'],
                reverse=True
            )[:5]
        }

    logger.info(f"Completed pain point linking for {len(pain_point_analysis)} pain points")
    return pain_point_analysis


# ============================================================================
# COMPREHENSIVE ANALYSIS SUMMARY
# ============================================================================

def generate_comprehensive_analysis_summary(
    brand: Brand,
    campaign: Campaign,
    threads: List[Thread],
    pain_points: List[PainPoint],
    influencers: List[Dict],
    pain_point_analysis: Dict[str, Dict]
) -> Dict[str, Any]:
    """
    Generate comprehensive analysis summary for dashboard display.
    """
    logger.info("Generating comprehensive analysis summary")

    # Overall sentiment
    thread_sentiments = [t.sentiment_score for t in threads if hasattr(t, 'sentiment_score')]
    avg_sentiment = statistics.mean(thread_sentiments) if thread_sentiments else 0.0

    # Influencer breakdown
    high_influence = [inf for inf in influencers if inf['influence_score'] > 70]
    advocates = [inf for inf in influencers if inf['sentiment_towards_brand'] > 0.2]
    critics = [inf for inf in influencers if inf['sentiment_towards_brand'] < -0.2]

    # Urgent pain points (urgency >= 5)
    urgent_pain_points = [
        analysis for analysis in pain_point_analysis.values()
        if analysis['urgency_score'] >= 5
    ]
    urgent_pain_points.sort(key=lambda x: x['urgency_score'], reverse=True)

    # Top communities
    community_stats = {}
    for thread in threads:
        if thread.community:
            comm_name = thread.community.name
            if comm_name not in community_stats:
                community_stats[comm_name] = {
                    'name': comm_name,
                    'platform': getattr(thread.community, 'platform', 'reddit'),
                    'thread_count': 0,
                    'total_sentiment': 0.0
                }
            community_stats[comm_name]['thread_count'] += 1
            if hasattr(thread, 'sentiment_score'):
                community_stats[comm_name]['total_sentiment'] += thread.sentiment_score

    top_communities = sorted(
        community_stats.values(),
        key=lambda x: x['thread_count'],
        reverse=True
    )[:10]

    for comm in top_communities:
        comm['avg_sentiment'] = comm['total_sentiment'] / max(comm['thread_count'], 1)

    # Generate key insights
    key_insights = []

    if len(high_influence) > 0:
        key_insights.append(
            f"Identified {len(high_influence)} high-influence users (score > 70) actively discussing {brand.name}"
        )

    if len(advocates) > len(critics):
        key_insights.append(
            f"Positive sentiment dominates: {len(advocates)} advocates vs {len(critics)} critics"
        )
    elif len(critics) > len(advocates):
        key_insights.append(
            f"⚠️ Negative sentiment detected: {len(critics)} critics vs {len(advocates)} advocates"
        )

    if urgent_pain_points:
        key_insights.append(
            f"{len(urgent_pain_points)} urgent pain points require immediate attention"
        )

    if top_communities:
        top_comm = top_communities[0]
        key_insights.append(
            f"Most active community: {top_comm['name']} with {top_comm['thread_count']} discussions"
        )

    if avg_sentiment > 0.3:
        key_insights.append(f"Overall sentiment is positive ({avg_sentiment:.2f}), indicating good brand perception")
    elif avg_sentiment < -0.3:
        key_insights.append(f"Overall sentiment is negative ({avg_sentiment:.2f}), requires brand response strategy")

    # Compile summary
    summary = {
        'overview': {
            'total_threads': len(threads),
            'total_influencers': len(influencers),
            'total_pain_points': len(pain_points),
            'overall_sentiment': round(avg_sentiment, 2),
            'analysis_timestamp': datetime.now().isoformat()
        },
        'influencer_breakdown': {
            'total_influencers': len(influencers),
            'high_influence_count': len(high_influence),
            'advocates': len(advocates),
            'critics': len(critics),
            'neutral': len(influencers) - len(advocates) - len(critics)
        },
        'pain_point_analysis': {
            'total_pain_points': len(pain_points),
            'urgent_pain_points': urgent_pain_points
        },
        'community_insights': {
            'total_communities': len(community_stats),
            'top_communities': top_communities
        },
        'key_insights': key_insights
    }

    logger.info(f"Generated summary with {len(key_insights)} key insights")
    return summary

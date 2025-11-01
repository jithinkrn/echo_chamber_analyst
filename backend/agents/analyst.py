"""
Analyst Agent - Unified Content & Influencer Analysis

This module consolidates all analysis capabilities into a single Analyst Agent:
- Content analysis and insight generation
- Influencer identification and scoring
- Pain point to influencer linking
- Comprehensive summaries with impact metrics
- AI-powered key insights generation
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import json
import re

from django.db.models import Avg, Count, Sum, Q
from common.models import Thread, Influencer, Brand, Campaign, Community, PainPoint

# LangChain imports for AI-powered insights
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Initialize OpenAI LLM for insight generation
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.3,  # Slightly higher for more creative insights
    max_tokens=3000
)


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
# AI-POWERED INSIGHT GENERATION FOR BRAND ANALYTICS
# ============================================================================

def generate_ai_powered_insights_from_brand_analytics(
    brand: Brand,
    kpis: Dict[str, Any],
    communities: List[Dict],
    pain_points: List[Dict],
    influencers: List[Dict]
) -> List[str]:
    """
    Generate AI-powered insights based on Brand Analytics dashboard data using OpenAI o1-mini reasoning model.

    This is specifically for the dashboard's "AI-Powered Key Insights" section,
    which displays insights based on overall brand performance metrics.

    Args:
        brand: Brand instance
        kpis: Dictionary of brand KPIs (from get_brand_dashboard_kpis)
        communities: List of community data (from get_brand_community_watchlist)
        pain_points: List of pain point data (from get_brand_top_pain_points)
        influencers: List of influencer data (from get_brand_influencer_pulse)

    Returns:
        List of 6 AI-generated insight strings for dashboard display
    """
    logger.info(f"🧠 Generating AI-powered insights using OpenAI o1-mini for Brand: {brand.name}")

    try:
        from openai import OpenAI
        import os
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Prepare comprehensive dashboard data summary
        dashboard_data = f"""BRAND ANALYTICS DASHBOARD DATA - {brand.name}

INDUSTRY: {brand.industry or 'Not specified'}
ANALYSIS PERIOD: Last 6 completed months

═══════════════════════════════════════════════════════════════

📊 KEY PERFORMANCE INDICATORS (KPIs):
────────────────────────────────────────────────────────────────
• Active Campaigns: {kpis.get('active_campaigns', 0)}
• High-Echo Communities (score ≥7.0): {kpis.get('high_echo_communities', 0)} communities
  └─ Trend: {kpis.get('high_echo_change_percent', 0):+.1f}% change
• New Pain Points: {kpis.get('new_pain_points_above_50', 0)} unique keywords appearing in latest completed month only
  └─ Change: {kpis.get('new_pain_points_change', 0)} new issues
• Positivity Ratio: {kpis.get('positivity_ratio', 0):.1f}% (derived from sentiment analysis)
  └─ Trend: {kpis.get('positivity_change_pp', 0):+.1f} percentage points change

═══════════════════════════════════════════════════════════════

🌐 COMMUNITY WATCHLIST ({len(communities)} communities total):
────────────────────────────────────────────────────────────────
Top Communities by Echo Score:
{chr(10).join([f"  {i+1}. {c.get('name', 'Unknown')} ({c.get('platform', 'unknown')})"
              f"     • Echo Score: {c.get('echo_score', 0):.1f}/100"
              f"     • Members: {c.get('member_count', 0):,}"
              f"     • Key Influencer: {c.get('key_influencer', 'Unknown')} ({c.get('influencer_post_count', 0)} posts, {c.get('influencer_engagement', 0)} engagement)"
               for i, c in enumerate(communities[:5])])}

Echo Score Formula: Thread Volume (40%) + Pain Point Intensity (30%) + Engagement Depth (30%)

═══════════════════════════════════════════════════════════════

⚠️ PAIN POINT TRENDS ({len(pain_points)} total pain points):
────────────────────────────────────────────────────────────────
Top Growing Pain Points:
{chr(10).join([f"  • {pp.get('keyword', 'Unknown')}"
              f"     └─ {pp.get('mention_count', 0)} total mentions across communities"
              f"     └─ Growth Rate: +{pp.get('growth_percentage', 0):.0f}% month-over-month"
              f"     └─ Sentiment: {pp.get('sentiment_score', 0):.2f} (scale: -1 to +1)"
               for pp in pain_points[:5]])}

═══════════════════════════════════════════════════════════════

👥 INFLUENCER PULSE ({len(influencers)} influencers tracked):
────────────────────────────────────────────────────────────────
Top Influencers:
{chr(10).join([f"  • @{inf.get('handle', 'Unknown')} ({inf.get('platform', 'unknown')})"
              f"     └─ Reach: {inf.get('reach', 0):,} followers"
              f"     └─ Engagement Rate: {inf.get('engagement_rate', 0):.1f}%"
              f"     └─ Advocacy Score: {inf.get('advocacy_score', 0):.1f}/10"
               for inf in influencers[:5]])}

═══════════════════════════════════════════════════════════════"""

        # Use OpenAI reasoning model for deep analysis
        # Try o1-mini first, fallback to gpt-4 if not accessible
        try:
            response = client.chat.completions.create(
                model="o1-mini",  # OpenAI's reasoning model
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are an expert brand intelligence analyst. Analyze the following Brand Analytics Dashboard data and generate exactly 6 strategic, actionable insights.

{dashboard_data}

ANALYSIS INSTRUCTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate exactly 6 insights that cover:

1. BRAND HEALTH ASSESSMENT: Evaluate overall brand perception based on echo scores, positivity ratio, and community engagement patterns. Identify if the brand is in a strong, moderate, or concerning position.

2. COMMUNITY ENGAGEMENT OPPORTUNITIES: Analyze the community watchlist data to identify which communities present the best opportunities for brand advocacy, partnerships, or crisis management. Look for patterns in echo scores and influencer activity.

3. PAIN POINT ANALYSIS: Examine the pain points data to identify critical customer experience issues. Prioritize by growth rate and sentiment. Suggest if these are product quality issues, service gaps, or perception problems.

4. INFLUENCER STRATEGY: Evaluate the influencer landscape to identify partnership opportunities, potential brand advocates, or areas where influencer engagement is weak. Consider reach, engagement, and advocacy scores.

5. DATA QUALITY & COVERAGE: Assess whether the monitoring coverage is sufficient. Look for gaps (e.g., zero campaigns, missing influencers, limited communities) that suggest need for expanded data collection.

6. STRATEGIC RECOMMENDATIONS: Provide prioritized action items based on the most critical findings. Focus on immediate business impact and feasibility.

FORMAT REQUIREMENTS:
• Return ONLY 6 insights, numbered 1-6
• Each insight must be 1-2 sentences maximum
• Be specific with actual numbers from the data
• Focus on actionable recommendations
• Use clear, executive-level language
• NO introductions, NO conclusions, NO preamble
• Start directly with "1. [insight]"

Example format:
1. [First insight with specific numbers and action]
2. [Second insight with specific numbers and action]
...
6. [Sixth insight with specific numbers and action]"""
                    }
                ]
            )
            logger.info("✅ Successfully used OpenAI o1-mini for insights")
        except Exception as o1_error:
            logger.warning(f"⚠️  o1-mini not accessible ({str(o1_error)}), falling back to gpt-4")
            # Fallback to GPT-4
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert brand intelligence analyst specializing in social media analytics and brand perception analysis."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze the following Brand Analytics Dashboard data and generate exactly 6 strategic, actionable insights.

{dashboard_data}

ANALYSIS INSTRUCTIONS:
Generate exactly 6 insights covering: brand health assessment, community engagement opportunities, pain point analysis, influencer strategy, data quality assessment, and strategic recommendations.

FORMAT: Return ONLY 6 insights, numbered 1-6. Each must be 1-2 sentences maximum. Be specific with actual numbers from the data. Focus on actionable recommendations.

Example:
1. [insight with numbers and action]
2. [insight with numbers and action]
...
6. [insight with numbers and action]"""
                    }
                ],
                temperature=0.7,
                max_tokens=800
            )

        insights_text = response.choices[0].message.content.strip()
        
        # Parse the numbered insights
        insights = []
        lines = insights_text.split('\n')
        for line in lines:
            line = line.strip()
            # Match numbered lines (1., 2., etc. or 1), 2), etc.)
            if re.match(r'^\d+[\.)]\s+', line):
                # Remove the number prefix
                insight = re.sub(r'^\d+[\.)]\s+', '', line).strip()
                if insight and len(insight) > 20:  # Filter out too-short lines
                    insights.append(insight)

        # Fallback: if parsing failed, try alternative parsing
        if len(insights) < 6:
            insights = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith('#') and len(line.strip()) > 30
            ][:6]

        logger.info(f"✅ Generated {len(insights)} AI-powered insights using OpenAI o1-mini")

        # Ensure we have exactly 6 insights (pad with fallbacks if needed)
        while len(insights) < 6 and len(insights) > 0:
            insights.append(f"Monitor ongoing trends in {brand.name} brand discussions for emerging opportunities and risks")

        return insights[:6]

    except Exception as e:
        logger.error(f"❌ Error generating AI insights with OpenAI o1-mini: {str(e)}")
        # Return rule-based fallback insights
        return generate_fallback_insights_from_brand_analytics(brand, kpis, communities, pain_points)


def generate_fallback_insights_from_brand_analytics(
    brand: Brand,
    kpis: Dict[str, Any],
    communities: List[Dict],
    pain_points: List[Dict]
) -> List[str]:
    """
    Generate fallback insights from Brand Analytics when AI generation fails.
    Uses rule-based logic.
    """
    insights = []

    # Insight 1: Campaign activity
    active_campaigns = kpis.get('active_campaigns', 0)
    if active_campaigns > 0:
        insights.append(
            f"{active_campaigns} active campaigns monitoring {brand.name}, "
            f"providing comprehensive brand intelligence across multiple channels"
        )

    # Insight 2: Echo chambers
    high_echo = kpis.get('high_echo_communities', 0)
    echo_change = kpis.get('high_echo_change_percent', 0)
    if high_echo > 0:
        trend = "increasing" if echo_change > 0 else "decreasing" if echo_change < 0 else "stable"
        insights.append(
            f"{high_echo} high-echo communities identified with {trend} trend ({echo_change:+.1f}%), "
            f"requiring strategic engagement to prevent information silos"
        )

    # Insight 3: Pain points
    pain_point_count = kpis.get('new_pain_points_above_50', 0)
    if pain_point_count > 0:
        insights.append(
            f"{pain_point_count} rapidly growing pain points (>50% growth) detected, "
            f"demanding immediate brand response and mitigation strategies"
        )

    # Insight 4: Sentiment
    positivity = kpis.get('positivity_ratio', 0)
    positivity_change = kpis.get('positivity_change_pp', 0)
    if positivity > 60:
        insights.append(
            f"Strong positive sentiment at {positivity:.1f}% ({positivity_change:+.1f} pp change), "
            f"indicating healthy brand perception and advocacy opportunity"
        )
    elif positivity < 40:
        insights.append(
            f"Concerning sentiment at {positivity:.1f}% ({positivity_change:+.1f} pp change), "
            f"requiring immediate reputation management and community outreach"
        )

    # Insight 5: Top community
    if communities and len(communities) > 0:
        top_comm = communities[0]
        key_inf = top_comm.get('key_influencer', 'Unknown')
        insights.append(
            f"Most active community '{top_comm.get('name', 'Unknown')}' with echo score of {top_comm.get('echo_score', 0):.1f} "
            f"features key influencer '{key_inf}', presenting strategic partnership opportunity"
        )

    # Insight 6: Top pain point
    if pain_points and len(pain_points) > 0:
        top_pain = pain_points[0]
        insights.append(
            f"Critical issue '{top_pain.get('keyword', 'Unknown')}' showing {top_pain.get('growth_percentage', 0):.0f}% growth "
            f"with {top_pain.get('mention_count', 0)} mentions requires urgent attention"
        )

    return insights[:6]


# ============================================================================
# CAMPAIGN AI INSIGHTS GENERATION (FOR CUSTOM CAMPAIGNS)
# ============================================================================

def generate_campaign_ai_insights(
    campaign: Campaign,
    brand: Brand,
    collected_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate AI-powered insights for a specific custom campaign.

    This is SEPARATE from Brand Analytics insights. These insights are
    campaign-specific and based on data collected during campaign execution.

    Args:
        campaign: Campaign instance
        brand: Brand instance
        collected_data: Dictionary containing campaign collection results
            - communities: List of communities monitored
            - threads: List of threads collected
            - pain_points: List of pain points identified

    Returns:
        List of campaign insight objects with structure:
        {
            "category": str,
            "insight": str,
            "priority": "high"|"medium"|"low",
            "action_items": [str, ...]
        }
    """
    logger.info(f"Generating Campaign AI Insights for campaign: {campaign.name}")

    try:
        # Extract campaign data
        num_communities = len(collected_data.get("communities", []))
        num_threads = len(collected_data.get("threads", []))
        num_pain_points = len(collected_data.get("pain_points", []))

        # Get top pain points
        pain_points = collected_data.get("pain_points", [])
        top_pain_points = sorted(pain_points, key=lambda x: x.get('mention_count', 0), reverse=True)[:5]

        # Calculate average sentiment
        threads = collected_data.get("threads", [])
        avg_sentiment = sum(t.get('sentiment_score', 0.0) for t in threads) / len(threads) if threads else 0.0
        sentiment_label = "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "neutral"

        # Get top communities by echo score
        communities = collected_data.get("communities", [])
        top_communities = sorted(communities, key=lambda x: x.get('echo_score', 0), reverse=True)[:3]

        # Build prompt for LLM
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert campaign analyst for social media monitoring campaigns.
            Generate 3-5 actionable insights specifically for THIS campaign's performance and findings.

            Guidelines:
            - Focus on THIS specific campaign's data and results
            - Provide actionable recommendations for campaign optimization
            - Identify specific trends and patterns in the collected data
            - Suggest concrete next steps for campaign managers
            - Prioritize insights by urgency (high/medium/low)
            - Each insight should have 2-4 specific action items

            Format your response as a JSON array of objects, each with:
            - "category": Brief category name (e.g., "Community Engagement", "Pain Point Alert")
            - "insight": Clear, specific insight about the campaign (1-2 sentences)
            - "priority": "high", "medium", or "low"
            - "action_items": Array of 2-4 specific, actionable steps

            Return ONLY the JSON array, no other text."""),

            HumanMessage(content=f"""Analyze this campaign's data and generate 3-5 actionable insights:

CAMPAIGN: {campaign.name}
BRAND: {brand.name}
CAMPAIGN STATUS: {campaign.status}

DATA COLLECTED:
- Communities Monitored: {num_communities}
- Discussions Analyzed: {num_threads}
- Pain Points Identified: {num_pain_points}
- Overall Sentiment: {sentiment_label} ({avg_sentiment:.2f})

TOP PAIN POINTS:
{chr(10).join([f"- {pp['keyword']}: {pp['mention_count']} mentions (growth: {pp.get('growth_percentage', 0):.0f}%)"
               for pp in top_pain_points[:3]]) if top_pain_points else "- No pain points identified yet"}

TOP COMMUNITIES (by echo score):
{chr(10).join([f"- {c['name']} ({c['platform']}): echo score {c['echo_score']:.1f}, {c.get('member_count', 0)} members"
               for c in top_communities]) if top_communities else "- No communities identified yet"}

Generate insights focusing on:
1. Campaign performance and effectiveness
2. Community engagement patterns specific to this campaign
3. Critical pain points requiring immediate attention
4. Opportunities for campaign optimization
5. Recommended next steps for campaign managers

Return ONLY a JSON array of insight objects.""")
        ])

        # Generate insights using LLM
        response = llm.invoke(prompt.format_messages())
        insights_text = response.content.strip()

        # Parse JSON response
        import re

        # Extract JSON from response
        json_match = re.search(r'\[.*\]', insights_text, re.DOTALL)
        if json_match:
            insights_json = json.loads(json_match.group(0))
        else:
            # Fallback to rule-based insights
            insights_json = generate_fallback_campaign_insights(campaign, brand, collected_data)

        logger.info(f"Generated {len(insights_json)} Campaign AI Insights")

        return insights_json

    except Exception as e:
        logger.error(f"Error generating Campaign AI Insights: {str(e)}")
        # Return fallback insights
        return generate_fallback_campaign_insights(campaign, brand, collected_data)


def generate_fallback_campaign_insights(
    campaign: Campaign,
    brand: Brand,
    collected_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate fallback campaign insights when AI generation fails.
    Uses rule-based logic.
    """
    insights = []

    num_threads = len(collected_data.get("threads", []))
    num_pain_points = len(collected_data.get("pain_points", []))
    pain_points = collected_data.get("pain_points", [])

    # Insight 1: Data collection status
    if num_threads > 50:
        insights.append({
            "category": "Data Collection Success",
            "insight": f"Campaign has successfully collected {num_threads} discussions, providing robust data for analysis.",
            "priority": "medium",
            "action_items": [
                "Review top discussions for key themes",
                "Identify most active communities for targeted engagement",
                "Schedule regular data refresh to maintain currency"
            ]
        })
    elif num_threads > 0:
        insights.append({
            "category": "Data Collection Status",
            "insight": f"Campaign has collected {num_threads} discussions. Consider expanding data collection scope for more comprehensive insights.",
            "priority": "medium",
            "action_items": [
                "Review and expand campaign keywords",
                "Add more target communities",
                "Increase collection frequency"
            ]
        })

    # Insight 2: Pain points
    if num_pain_points > 0:
        top_pain = sorted(pain_points, key=lambda x: x.get('mention_count', 0), reverse=True)[0]
        insights.append({
            "category": "Critical Pain Point",
            "insight": f"Top issue '{top_pain['keyword']}' identified with {top_pain['mention_count']} mentions, requiring brand response strategy.",
            "priority": "high",
            "action_items": [
                "Develop response strategy for this pain point",
                "Monitor sentiment trends around this issue",
                "Engage with affected users directly",
                "Create content addressing this concern"
            ]
        })

    # Insight 3: Campaign optimization
    insights.append({
        "category": "Campaign Optimization",
        "insight": f"Campaign '{campaign.name}' is actively monitoring {brand.name}. Regular reviews recommended for optimal performance.",
        "priority": "medium",
        "action_items": [
            "Review campaign metrics weekly",
            "Adjust targeting based on findings",
            "Update stakeholders on key insights"
        ]
    })

    return insights[:5]  # Return up to 5 fallback insights


def generate_ai_powered_insights(
    brand: Brand,
    campaign: Campaign,
    summary_data: Dict[str, Any]
) -> List[str]:
    """
    DEPRECATED - DO NOT USE

    This function is deprecated and not used in the current architecture.
    Use generate_ai_powered_insights_from_brand_analytics() for Brand Analytics insights.
    Use generate_campaign_ai_insights() for Campaign-specific insights.

    Args:
        brand: Brand instance
        campaign: Campaign instance
        summary_data: Dictionary containing analysis summary data

    Returns:
        List of AI-generated insight strings
    """
    logger.info(f"Generating AI-powered insights for brand: {brand.name}")

    try:
        # Prepare context for the LLM
        context = {
            "brand_name": brand.name,
            "brand_industry": brand.industry,
            "overview": summary_data.get('overview', {}),
            "influencer_breakdown": summary_data.get('influencer_breakdown', {}),
            "pain_point_analysis": summary_data.get('pain_point_analysis', {}),
            "community_insights": summary_data.get('community_insights', {}),
            "basic_insights": summary_data.get('key_insights', [])
        }

        # Create the prompt for insight generation
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert brand analyst specializing in social media analytics,
            community sentiment analysis, and influencer marketing. Your role is to generate strategic,
            actionable insights based on brand analytics data.

            Guidelines:
            - Focus on actionable insights that drive business decisions
            - Identify emerging trends and opportunities
            - Highlight risks and areas requiring immediate attention
            - Connect multiple data points to uncover deeper patterns
            - Be specific and quantitative where possible
            - Prioritize insights by business impact
            - Keep each insight concise (1-2 sentences)
            - Generate exactly 6 unique, high-value insights"""),

            HumanMessage(content=f"""Based on the following brand analytics data, generate 6 strategic insights:

Brand: {context['brand_name']}
Industry: {context['brand_industry']}

Analytics Overview:
- Total Threads Analyzed: {context['overview'].get('total_threads', 0)}
- Total Influencers Identified: {context['overview'].get('total_influencers', 0)}
- Total Pain Points: {context['overview'].get('total_pain_points', 0)}
- Overall Sentiment: {context['overview'].get('overall_sentiment', 0):.2f}

Influencer Breakdown:
- Total Influencers: {context['influencer_breakdown'].get('total_influencers', 0)}
- High-Influence Count (>70): {context['influencer_breakdown'].get('high_influence_count', 0)}
- Brand Advocates: {context['influencer_breakdown'].get('advocates', 0)}
- Critics: {context['influencer_breakdown'].get('critics', 0)}
- Neutral: {context['influencer_breakdown'].get('neutral', 0)}

Pain Point Analysis:
- Total Pain Points: {context['pain_point_analysis'].get('total_pain_points', 0)}
- Urgent Pain Points (score ≥5): {len(context['pain_point_analysis'].get('urgent_pain_points', []))}

Top Urgent Pain Points:
{chr(10).join([f"  • {pp['pain_point']} (urgency: {pp['urgency_score']}/10, {pp['frequency']} mentions, {pp['influencer_count']} influencers)"
               for pp in context['pain_point_analysis'].get('urgent_pain_points', [])[:5]])}

Community Insights:
- Total Communities: {context['community_insights'].get('total_communities', 0)}

Top Communities:
{chr(10).join([f"  • {comm['name']} ({comm['platform']}) - {comm['thread_count']} threads, sentiment: {comm.get('avg_sentiment', 0):.2f}"
               for comm in context['community_insights'].get('top_communities', [])[:5]])}

Please generate 6 actionable insights that:
1. Identify key opportunities for brand engagement
2. Highlight critical risks or issues requiring attention
3. Suggest strategic actions based on influencer dynamics
4. Recommend community engagement strategies
5. Provide competitive or market positioning insights
6. Suggest pain point mitigation strategies

Format each insight as a clear, standalone statement. Number them 1-6.""")
        ])

        # Generate insights using the LLM
        response = llm.invoke(prompt.format_messages())

        # Parse the response
        insights_text = response.content

        # Extract numbered insights
        insights = []
        lines = insights_text.split('\n')
        for line in lines:
            line = line.strip()
            # Match numbered lines (1., 2., etc. or 1), 2), etc.)
            if re.match(r'^\d+[\.)]\s+', line):
                # Remove the number prefix
                insight = re.sub(r'^\d+[\.)]\s+', '', line).strip()
                if insight:
                    insights.append(insight)

        # Fallback: if parsing failed, try to split by newlines and filter
        if len(insights) < 6:
            insights = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith('#') and len(line.strip()) > 20
            ][:6]

        logger.info(f"Generated {len(insights)} AI-powered insights")

        return insights[:6] if len(insights) >= 6 else insights

    except Exception as e:
        logger.error(f"Error generating AI-powered insights: {str(e)}")
        # Return fallback insights based on basic data
        return generate_fallback_insights(brand, summary_data)


def generate_fallback_insights(brand: Brand, summary_data: Dict[str, Any]) -> List[str]:
    """
    Generate fallback insights when AI generation fails.
    Uses rule-based logic to create meaningful insights.
    """
    insights = []

    influencer_breakdown = summary_data.get('influencer_breakdown', {})
    pain_point_analysis = summary_data.get('pain_point_analysis', {})
    overview = summary_data.get('overview', {})

    # Insight 1: High-influence users
    high_influence = influencer_breakdown.get('high_influence_count', 0)
    if high_influence > 0:
        insights.append(
            f"Identified {high_influence} high-influence users actively discussing {brand.name}, "
            f"representing key opportunities for strategic brand partnerships and advocacy programs"
        )

    # Insight 2: Sentiment analysis
    advocates = influencer_breakdown.get('advocates', 0)
    critics = influencer_breakdown.get('critics', 0)
    if advocates > critics:
        insights.append(
            f"Positive sentiment dominates with {advocates} advocates vs {critics} critics, "
            f"indicating strong brand health and organic advocacy potential"
        )
    elif critics > advocates:
        insights.append(
            f"Critical alert: {critics} critics vs {advocates} advocates detected, "
            f"requiring immediate brand response strategy and reputation management"
        )

    # Insight 3: Urgent pain points
    urgent_pain_points = pain_point_analysis.get('urgent_pain_points', [])
    if urgent_pain_points:
        top_pain = urgent_pain_points[0]
        insights.append(
            f"Most urgent issue: '{top_pain['pain_point']}' (urgency {top_pain['urgency_score']}/10) "
            f"discussed by {top_pain['influencer_count']} influencers, demanding executive-level attention"
        )

    # Insight 4: Community engagement
    communities = summary_data.get('community_insights', {})
    total_communities = communities.get('total_communities', 0)
    if total_communities > 0:
        top_communities = communities.get('top_communities', [])
        if top_communities:
            top_comm = top_communities[0]
            insights.append(
                f"Highest engagement in '{top_comm['name']}' community with {top_comm['thread_count']} "
                f"discussions, presenting prime opportunity for targeted community management"
            )

    # Insight 5: Overall sentiment
    sentiment = overview.get('overall_sentiment', 0)
    if sentiment > 0.3:
        insights.append(
            f"Strong positive sentiment ({sentiment:.2f}) indicates excellent brand perception "
            f"and opportunity to amplify positive narratives through influencer partnerships"
        )
    elif sentiment < -0.3:
        insights.append(
            f"Concerning negative sentiment ({sentiment:.2f}) requires immediate crisis communication "
            f"strategy and proactive community engagement initiatives"
        )

    # Insight 6: Data volume
    total_threads = overview.get('total_threads', 0)
    if total_threads > 100:
        insights.append(
            f"Significant conversation volume ({total_threads} threads) demonstrates high brand awareness "
            f"and market mindshare, warranting dedicated community monitoring resources"
        )

    return insights[:6]


# ============================================================================
# COMPREHENSIVE ANALYSIS SUMMARY (DEPRECATED)
# ============================================================================
# NOTE: These functions are deprecated and not used in the current architecture.
# The new architecture uses:
# - generate_ai_powered_insights_from_brand_analytics() for Brand Analytics
# - generate_campaign_ai_insights() for Campaign-specific insights

def generate_comprehensive_analysis_summary(
    brand: Brand,
    campaign: Campaign,
    threads: List[Thread],
    pain_points: List[PainPoint],
    influencers: List[Dict],
    pain_point_analysis: Dict[str, Dict]
) -> Dict[str, Any]:
    """
    DEPRECATED - DO NOT USE

    This function is deprecated. Use the new architecture functions instead.
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

    # Compile basic summary first (needed for AI insights)
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
        'key_insights': []  # Will be filled by AI
    }

    # Generate AI-powered key insights
    logger.info("Generating AI-powered key insights")
    ai_insights = generate_ai_powered_insights(brand, campaign, summary)
    summary['key_insights'] = ai_insights

    logger.info(f"Generated summary with {len(ai_insights)} AI-powered key insights")
    return summary

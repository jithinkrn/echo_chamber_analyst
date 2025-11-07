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
    influencers: List[Dict],
    heatmap_data: Dict[str, Any] = None
) -> List[str]:
    """
    Generate AI-powered insights based on Brand Analytics dashboard data using OpenAI o3-mini reasoning model.

    This is specifically for the dashboard's "AI-Powered Key Insights" section,
    which displays insights based on overall brand performance metrics.

    Args:
        brand: Brand instance
        kpis: Dictionary of brand KPIs (from get_brand_dashboard_kpis)
        communities: List of community data (from get_brand_community_watchlist)
        pain_points: List of pain point data (from get_brand_top_pain_points)
        influencers: List of influencer data (from get_brand_influencer_pulse)
        heatmap_data: Dictionary with chart data (community_pain_point_matrix, time_series_pain_points, total_mentions_series)

    Returns:
        List of 6 AI-generated insight strings for dashboard display
    """
    logger.info(f"🧠 Generating AI-powered insights using OpenAI o3-mini for Brand: {brand.name}")
    
    # Initialize heatmap_data if not provided
    if heatmap_data is None:
        heatmap_data = {
            'community_pain_point_matrix': [],
            'time_series_pain_points': [],
            'total_mentions_series': []
        }

    try:
        from openai import OpenAI
        import os
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Prepare comprehensive dashboard data summary including all chart data
        
        # Extract community pain point matrix insights
        community_pain_matrix_summary = ""
        if heatmap_data.get('community_pain_point_matrix'):
            community_pain_matrix_summary = "\n\n📈 COMMUNITY × PAIN POINT MATRIX (from bubble chart):\n" + "─" * 60 + "\n"
            for comm in heatmap_data['community_pain_point_matrix'][:5]:
                community_pain_matrix_summary += f"  • {comm.get('community_name', 'Unknown')} ({comm.get('platform', 'unknown')}) - Echo Score: {comm.get('echo_score', 0):.1f}\n"
                if comm.get('pain_points'):
                    for pp in comm['pain_points'][:3]:
                        community_pain_matrix_summary += f"    └─ {pp.get('keyword', 'Unknown')}: {pp.get('mention_count', 0)} mentions, +{pp.get('growth_percentage', 0):.0f}% growth, sentiment {pp.get('sentiment_score', 0):.2f}\n"
                else:
                    community_pain_matrix_summary += "    └─ No pain points tracked yet\n"
        
        # Extract time series trends
        time_series_summary = ""
        if heatmap_data.get('time_series_pain_points'):
            time_series_summary = "\n\n📊 PAIN POINT TRENDS OVER TIME (6-month time series):\n" + "─" * 60 + "\n"
            for pp_series in heatmap_data['time_series_pain_points'][:5]:
                keyword = pp_series.get('keyword', 'Unknown')
                total_mentions = pp_series.get('total_mentions', 0)
                growth_rate = pp_series.get('growth_rate', 0)
                time_series_summary += f"  • {keyword}: {total_mentions} total mentions, {growth_rate:+.1f}% MoM growth\n"
                
                # Show month-by-month breakdown
                if pp_series.get('time_series'):
                    recent_months = pp_series['time_series'][-3:]  # Last 3 months
                    month_data = ", ".join([f"{m['label']}: {m['mention_count']}" for m in recent_months])
                    time_series_summary += f"    └─ Recent trend: {month_data}\n"
        
        # Extract total mentions trend
        total_mentions_trend = ""
        if heatmap_data.get('total_mentions_series'):
            total_mentions_trend = "\n\n📉 TOTAL MENTION VOLUME TREND (all pain points combined):\n" + "─" * 60 + "\n"
            for month_data in heatmap_data['total_mentions_series']:
                total_mentions_trend += f"  • {month_data.get('label', 'Unknown')}: {month_data.get('total_mentions', 0):,} total mentions\n"
            
            # Calculate overall trend
            if len(heatmap_data['total_mentions_series']) >= 2:
                first_month = heatmap_data['total_mentions_series'][0].get('total_mentions', 0)
                last_month = heatmap_data['total_mentions_series'][-1].get('total_mentions', 0)
                if first_month > 0:
                    overall_growth = ((last_month - first_month) / first_month) * 100
                    trend_direction = "📈 INCREASING" if overall_growth > 0 else "📉 DECREASING"
                    total_mentions_trend += f"\n  Overall 6-month trend: {trend_direction} ({overall_growth:+.1f}%)\n"
        
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

═══════════════════════════════════════════════════════════════
{community_pain_matrix_summary}
═══════════════════════════════════════════════════════════════
{time_series_summary}
═══════════════════════════════════════════════════════════════
{total_mentions_trend}
═══════════════════════════════════════════════════════════════"""

        # Use OpenAI reasoning model for deep analysis
        # Try o3-mini first, fallback to gpt-4 if not accessible
        try:
            response = client.chat.completions.create(
                model="o3-mini",  # OpenAI's reasoning model
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are an expert brand intelligence analyst. Analyze the following Brand Analytics Dashboard data and generate exactly 6 strategic, actionable insights.

{dashboard_data}

ANALYSIS INSTRUCTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyze ALL sections including the KPIs, Community Watchlist, Pain Point Trends, Influencer Pulse, AND the chart data (Community × Pain Point Matrix, Pain Point Trends Over Time, Total Mention Volume Trend).

Generate exactly 6 insights that cover:

1. BRAND HEALTH ASSESSMENT: Evaluate overall brand perception based on echo scores, positivity ratio, community engagement patterns, and the 6-month mention volume trend. Identify if the brand is in a strong, moderate, or concerning position. Reference specific trend data.

2. COMMUNITY ENGAGEMENT OPPORTUNITIES: Analyze the community watchlist AND the Community × Pain Point Matrix to identify which communities present the best opportunities for brand advocacy, partnerships, or crisis management. Look for communities with high pain points and growing mention counts.

3. PAIN POINT ANALYSIS: Examine BOTH the top growing pain points list AND the time series chart data to identify critical customer experience issues. Note patterns like accelerating growth, seasonal spikes, or consistent decline. Prioritize by growth trajectory and sentiment.

4. INFLUENCER STRATEGY: Evaluate the influencer landscape to identify partnership opportunities, potential brand advocates, or areas where influencer engagement is weak. Cross-reference with community data to see which communities lack strong influencer presence.

5. TREND ANALYSIS: Use the 6-month time series data to identify patterns: Are mentions increasing or decreasing overall? Which pain points show accelerating vs. decelerating trends? Are any pain points showing seasonal patterns?

6. STRATEGIC RECOMMENDATIONS: Provide prioritized action items based on the most critical findings from ALL data sources (KPIs, charts, trends). Focus on immediate business impact and feasibility. Reference specific numbers from the time series and matrix data.

FORMAT REQUIREMENTS:
• Return ONLY 6 insights, numbered 1-6
• Each insight must be 1-2 sentences maximum
• Be specific with actual numbers from the data (including chart data)
• Reference trends, growth rates, and time series patterns
• Focus on actionable recommendations
• Use clear, executive-level language
• NO introductions, NO conclusions, NO preamble
• Start directly with "1. [insight]"

Example format:
1. [First insight with specific KPI numbers and trend data]
2. [Second insight with community matrix and growth patterns]
...
6. [Sixth insight with time series insights and strategic action]"""
                    }
                ]
            )
            logger.info("✅ Successfully used OpenAI o3-mini for insights")
        except Exception as o1_error:
            logger.warning(f"⚠️  o3-mini not accessible ({str(o1_error)}), falling back to gpt-4")
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
Analyze ALL sections including KPIs, Community Watchlist, Pain Point Trends, Influencer Pulse, AND chart data (Community × Pain Point Matrix, Pain Point Trends Over Time, Total Mention Volume Trend).

Generate exactly 6 insights covering:
1. Brand health with 6-month trend analysis
2. Community engagement using matrix data
3. Pain point analysis with time series patterns
4. Influencer strategy
5. Trend patterns from time series
6. Strategic recommendations with chart insights

FORMAT: Return ONLY 6 insights, numbered 1-6. Each must be 1-2 sentences maximum. Reference specific numbers from KPIs AND chart data (trends, growth rates, time series). Focus on actionable recommendations.

Example:
1. [insight with KPI and trend numbers]
2. [insight with matrix and growth data]
...
6. [insight with time series patterns and action]"""
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
# CUSTOM CAMPAIGN REPORT GENERATION
# ============================================================================
# This is THE ONLY function used for custom campaigns.
# Brand Analytics uses generate_ai_powered_insights_from_brand_analytics() instead.
# ============================================================================

def generate_strategic_campaign_report(
    campaign: Campaign,
    brand: Brand,
    collected_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate strategic campaign report aligned with campaign objectives.

    This is for CUSTOM CAMPAIGNS only. Unlike Brand Analytics (which collects
    pain points generically), custom campaigns are strategic initiatives with
    specific business objectives (e.g., "Increase retention 45% → 65%").

    This function analyzes collected data in the context of campaign objectives
    and generates a goal-oriented strategic report.

    Args:
        campaign: Campaign instance with objectives in metadata
        brand: Brand instance
        collected_data: Dictionary containing campaign collection results
            - communities: List of communities monitored
            - threads: List of threads collected
            - pain_points: List of pain points identified (if any)

    Returns:
        Strategic report dictionary with structure:
        {
            "executive_summary": str,
            "campaign_objective": str,
            "key_metrics": {
                "target": str,
                "baseline": str,
                "current_progress": str,
                "trend": str
            },
            "strategic_findings": [
                {
                    "finding": str,
                    "evidence": str,
                    "recommendation": str,
                    "priority": "high"|"medium"|"low"
                }
            ],
            "supporting_data": {
                "communities_analyzed": int,
                "discussions_reviewed": int,
                "sentiment_score": float,
                "top_themes": [str, ...]
            },
            "generated_at": str (ISO timestamp)
        }
    """
    logger.info(f"🎯 Generating Strategic Campaign Report for: {campaign.name}")

    try:
        from openai import OpenAI
        import os

        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Extract campaign objective
        campaign_objective = campaign.metadata.get('objectives', 'Monitor brand sentiment and engagement')

        # Extract collected data summary
        num_communities = len(collected_data.get("communities", []))
        num_threads = len(collected_data.get("threads", []))
        threads = collected_data.get("threads", [])

        # Calculate sentiment
        avg_sentiment = sum(t.get('sentiment_score', 0.0) for t in threads) / len(threads) if threads else 0.0
        sentiment_label = "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "neutral"

        # Get top communities
        communities = collected_data.get("communities", [])
        top_communities = sorted(communities, key=lambda x: x.get('echo_score', 0), reverse=True)[:3]

        # Extract top themes from threads
        pain_points = collected_data.get("pain_points", [])
        top_themes = [pp.get('keyword', '') for pp in sorted(pain_points, key=lambda x: x.get('mention_count', 0), reverse=True)[:5]]

        # Prepare data summary for LLM
        data_summary = f"""CAMPAIGN: {campaign.name}
BRAND: {brand.name}
OBJECTIVE: {campaign_objective}

DATA COLLECTED:
• Communities Analyzed: {num_communities}
• Discussions Reviewed: {num_threads}
• Sentiment: {sentiment_label} ({avg_sentiment:.2f})

TOP COMMUNITIES:
{chr(10).join([f"  • {c['name']} ({c.get('platform', 'unknown')}): {c.get('member_count', 0):,} members, echo score {c.get('echo_score', 0):.0f}"
               for c in top_communities]) if top_communities else "  • None identified yet"}

TOP DISCUSSION THEMES:
{chr(10).join([f"  • {theme}" for theme in top_themes]) if top_themes else "  • None identified yet"}

SAMPLE DISCUSSIONS:
{chr(10).join([f"  • '{t.get('title', 'Untitled')}' ({t.get('engagement', 0)} engagement, sentiment: {t.get('sentiment_score', 0):.2f})"
               for t in threads[:5]]) if threads else "  • No discussions yet"}"""

        # Generate strategic report using GPT-4
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a strategic business analyst specializing in data-driven campaign performance analysis.

Your task: Analyze collected social media data in the context of the campaign's business objective and generate a strategic report.

CRITICAL: This is NOT a generic brand monitoring report. This is a STRATEGIC CAMPAIGN with specific business goals.
- Focus on the stated objective (e.g., retention, sentiment shift, feature adoption, etc.)
- Generate findings that directly relate to achieving the objective
- Provide evidence-based recommendations aligned with the goal
- Estimate progress toward the objective based on available signals

Return your analysis as a JSON object with this EXACT structure:
{
  "executive_summary": "2-3 sentence summary of campaign progress toward objective",
  "key_metrics": {
    "target": "The campaign's target goal (extracted from objective)",
    "baseline": "Estimated baseline or starting point (if inferable from data, else 'TBD')",
    "current_progress": "Evidence-based assessment of progress (percentage or qualitative)",
    "trend": "Direction: 'improving', 'stable', 'declining', or 'insufficient data'"
  },
  "strategic_findings": [
    {
      "finding": "Key insight directly related to campaign objective",
      "evidence": "Data points from collected discussions supporting this finding",
      "recommendation": "Specific action to advance toward objective",
      "priority": "high|medium|low"
    }
  ],
  "next_steps": [
    "Immediate action item 1",
    "Immediate action item 2",
    "Immediate action item 3"
  ]
}

Generate EXACTLY 4 strategic findings. Focus on objective-relevant insights, not generic pain points."""
                },
                {
                    "role": "user",
                    "content": f"""Analyze this campaign data and generate a strategic report:

{data_summary}

Instructions:
1. Read the OBJECTIVE carefully - this defines success for the campaign
2. Analyze collected data for signals related to achieving that objective
3. Generate 4 strategic findings that help understand progress toward the goal
4. Provide evidence from actual discussions (titles, sentiment, themes)
5. Recommend actions that directly advance the objective

Return ONLY the JSON object, no other text."""
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )

        report_text = response.choices[0].message.content.strip()

        # Parse JSON response
        json_match = re.search(r'\{.*\}', report_text, re.DOTALL)
        if json_match:
            strategic_report = json.loads(json_match.group(0))
        else:
            # Fallback to rule-based report
            logger.warning("Failed to parse LLM response, using fallback report")
            strategic_report = generate_fallback_strategic_report(campaign, brand, collected_data)

        # Add supporting data
        strategic_report["supporting_data"] = {
            "communities_analyzed": num_communities,
            "discussions_reviewed": num_threads,
            "sentiment_score": round(avg_sentiment, 2),
            "top_themes": top_themes[:5]
        }

        # Add metadata
        strategic_report["campaign_objective"] = campaign_objective
        strategic_report["generated_at"] = datetime.now().isoformat()

        logger.info(f"✅ Generated strategic report with {len(strategic_report.get('strategic_findings', []))} findings")

        return strategic_report

    except Exception as e:
        logger.error(f"❌ Error generating strategic campaign report: {str(e)}")
        # Return fallback report
        return generate_fallback_strategic_report(campaign, brand, collected_data)


def generate_fallback_strategic_report(
    campaign: Campaign,
    brand: Brand,
    collected_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate fallback strategic report when AI generation fails.
    Uses rule-based logic.
    """
    campaign_objective = campaign.metadata.get('objectives', 'Monitor brand sentiment')
    num_threads = len(collected_data.get("threads", []))
    num_communities = len(collected_data.get("communities", []))
    threads = collected_data.get("threads", [])
    avg_sentiment = sum(t.get('sentiment_score', 0.0) for t in threads) / len(threads) if threads else 0.0

    return {
        "executive_summary": f"Campaign '{campaign.name}' is actively monitoring {num_threads} discussions across {num_communities} communities. Overall sentiment is {'positive' if avg_sentiment > 0 else 'neutral/negative'}. Continue data collection to establish baseline metrics.",
        "campaign_objective": campaign_objective,
        "key_metrics": {
            "target": "TBD (requires more data)",
            "baseline": "Establishing baseline",
            "current_progress": f"{num_threads} discussions analyzed",
            "trend": "insufficient data" if num_threads < 20 else "stable"
        },
        "strategic_findings": [
            {
                "finding": f"Campaign has collected {num_threads} discussions for analysis",
                "evidence": f"Data from {num_communities} communities provides initial insights",
                "recommendation": "Continue monitoring to establish trends and baseline metrics",
                "priority": "medium"
            },
            {
                "finding": f"Overall sentiment is {'positive' if avg_sentiment > 0.2 else 'negative' if avg_sentiment < -0.2 else 'neutral'} ({avg_sentiment:.2f})",
                "evidence": f"Average sentiment across {num_threads} discussions",
                "recommendation": "Track sentiment trends over time to measure progress",
                "priority": "medium"
            },
            {
                "finding": "Baseline data collection in progress",
                "evidence": f"{num_communities} communities being monitored",
                "recommendation": "Expand data collection scope for comprehensive analysis",
                "priority": "low"
            },
            {
                "finding": "Strategic insights require additional data",
                "evidence": "Initial collection phase",
                "recommendation": "Schedule next data collection cycle and review progress",
                "priority": "low"
            }
        ],
        "next_steps": [
            "Continue data collection across monitored communities",
            "Schedule weekly review of campaign metrics",
            "Establish baseline benchmarks for objective measurement"
        ],
        "supporting_data": {
            "communities_analyzed": num_communities,
            "discussions_reviewed": num_threads,
            "sentiment_score": round(avg_sentiment, 2),
            "top_themes": []
        },
        "generated_at": datetime.now().isoformat()
    }


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


# ============================================================================
# PDF REPORT GENERATION
# ============================================================================

def generate_strategic_report_pdf(campaign: Campaign, brand: Brand) -> bytes:
    """
    Generate a professional PDF report from the strategic campaign report.
    
    This function is called by the Analyst Agent to generate a downloadable
    PDF report containing all strategic findings, metrics, and recommendations.
    
    Args:
        campaign: Campaign instance with metadata['report']
        brand: Brand instance
        
    Returns:
        bytes: PDF file content
    """
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from io import BytesIO
    
    logger.info(f"📄 Analyst Agent: Generating PDF report for campaign '{campaign.name}'")
    
    # Get strategic report from campaign metadata
    if not campaign.metadata or 'report' not in campaign.metadata:
        raise ValueError(f"No strategic report found for campaign {campaign.id}")
    
    strategic_report = campaign.metadata['report']
    
    # Create PDF buffer
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=6,
        spaceBefore=6,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )
    
    # Title
    elements.append(Paragraph("Strategic Campaign Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Campaign Info
    campaign_info = [
        ["Campaign:", campaign.name],
        ["Brand:", brand.name],
        ["Type:", campaign.campaign_type.upper()],
        ["Status:", campaign.status.upper()],
        ["Generated:", datetime.now().strftime("%B %d, %Y at %H:%M")]
    ]
    
    info_table = Table(campaign_info, colWidths=[1.5*inch, 4.5*inch])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Executive Summary
    elements.append(Paragraph("Executive Summary", heading_style))
    exec_summary = strategic_report.get('executive_summary', 'No executive summary available.')
    elements.append(Paragraph(exec_summary, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Campaign Objective
    elements.append(Paragraph("Campaign Objective", heading_style))
    objective = strategic_report.get('campaign_objective', 'No objective specified.')
    # Split by newlines and create paragraphs for each section
    for section in objective.split('\n\n'):
        if section.strip():
            elements.append(Paragraph(section.strip().replace('\n', '<br/>'), body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Key Metrics
    elements.append(Paragraph("Key Metrics", heading_style))
    key_metrics = strategic_report.get('key_metrics', {})
    
    if key_metrics:
        metrics_data = [['Metric', 'Value']]
        for key, value in key_metrics.items():
            metric_name = key.replace('_', ' ').title()
            metrics_data.append([metric_name, str(value)])
        
        metrics_table = Table(metrics_data, colWidths=[2.5*inch, 3.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        elements.append(metrics_table)
    else:
        elements.append(Paragraph("No metrics available.", body_style))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Strategic Findings
    elements.append(Paragraph("Strategic Findings", heading_style))
    strategic_findings = strategic_report.get('strategic_findings', [])
    
    if strategic_findings:
        for idx, finding in enumerate(strategic_findings, 1):
            # Finding title with priority
            priority = finding.get('priority', 'medium').upper()
            priority_color = {
                'HIGH': '#dc2626',
                'MEDIUM': '#f59e0b',
                'LOW': '#3b82f6'
            }.get(priority, '#6b7280')
            
            finding_title = f"{idx}. {finding.get('finding', 'No finding specified')}"
            elements.append(Paragraph(finding_title, subheading_style))
            
            # Priority badge
            priority_text = f"<font color='{priority_color}'><b>Priority: {priority}</b></font>"
            elements.append(Paragraph(priority_text, body_style))
            
            # Evidence
            if finding.get('evidence'):
                evidence_text = f"<b>Evidence:</b> {finding.get('evidence')}"
                elements.append(Paragraph(evidence_text, body_style))
            
            # Recommendation
            if finding.get('recommendation'):
                rec_text = f"<b>Recommendation:</b> {finding.get('recommendation')}"
                elements.append(Paragraph(rec_text, body_style))
            
            elements.append(Spacer(1, 0.15*inch))
    else:
        elements.append(Paragraph("No strategic findings available.", body_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Supporting Data
    elements.append(Paragraph("Supporting Data", heading_style))
    supporting_data = strategic_report.get('supporting_data', {})
    
    if supporting_data:
        support_data_list = [
            ['Communities Analyzed', str(supporting_data.get('communities_analyzed', 0))],
            ['Discussions Reviewed', str(supporting_data.get('discussions_reviewed', 0))],
            ['Sentiment Score', f"{supporting_data.get('sentiment_score', 0):.2f}"],
        ]
        
        # Add top themes
        top_themes = supporting_data.get('top_themes', [])
        if top_themes:
            support_data_list.append(['Key Themes', ', '.join(top_themes)])
        
        support_table = Table(support_data_list, colWidths=[2.5*inch, 3.5*inch])
        support_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#111827')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(support_table)
    else:
        elements.append(Paragraph("No supporting data available.", body_style))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Next Steps
    next_steps = strategic_report.get('next_steps', [])
    if next_steps:
        elements.append(Paragraph("Recommended Next Steps", heading_style))
        for idx, step in enumerate(next_steps, 1):
            step_text = f"{idx}. {step}"
            elements.append(Paragraph(step_text, body_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF content
    pdf_content = buffer.getvalue()
    buffer.close()
    
    logger.info(f"✅ Analyst Agent: PDF report generated successfully ({len(pdf_content)} bytes)")
    
    return pdf_content

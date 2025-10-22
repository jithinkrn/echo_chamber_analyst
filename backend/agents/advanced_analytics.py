"""
Advanced Analytics Module for Enhanced Insight Generation

This module provides sophisticated analytics capabilities including:
- Advanced sentiment analysis with context understanding
- Trend detection and pattern recognition
- Competitive intelligence analysis
- Influencer identification and tracking
- Predictive analytics for pain point trends
- Multi-dimensional insight scoring
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import statistics

from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone

from common.models import (
    Campaign, ProcessedContent, Insight, PainPoint,
    Community, Thread, Influencer
)

logger = logging.getLogger(__name__)


class AdvancedSentimentAnalyzer:
    """Advanced sentiment analysis with context awareness and nuance detection."""

    def __init__(self):
        self.positive_modifiers = ['very', 'extremely', 'absolutely', 'really', 'super']
        self.negative_modifiers = ['barely', 'hardly', 'somewhat', 'slightly']
        self.negation_words = ['not', 'never', 'no', 'neither', 'nor', "n't"]

    def analyze_sentiment_with_context(self, text: str, keywords: List[str]) -> Dict[str, Any]:
        """
        Perform advanced sentiment analysis with context awareness.

        Returns:
            Dict containing sentiment score, confidence, modifiers, and context
        """
        text_lower = text.lower()

        # Find keyword contexts
        keyword_sentiments = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                context_sentiment = self._analyze_keyword_context(text_lower, keyword.lower())
                keyword_sentiments.append(context_sentiment)

        # Calculate overall sentiment
        if keyword_sentiments:
            avg_sentiment = statistics.mean(keyword_sentiments)
            confidence = min(len(keyword_sentiments) / len(keywords), 1.0)
        else:
            avg_sentiment = 0.0
            confidence = 0.0

        # Detect sentiment modifiers
        modifiers = self._detect_sentiment_modifiers(text_lower)

        # Adjust for negations
        negation_count = sum(1 for word in self.negation_words if word in text_lower)
        if negation_count % 2 == 1:  # Odd number of negations
            avg_sentiment = -avg_sentiment

        return {
            'sentiment_score': round(avg_sentiment, 3),
            'confidence': round(confidence, 3),
            'keyword_sentiments': keyword_sentiments,
            'modifiers': modifiers,
            'negations_detected': negation_count,
            'sentiment_label': self._get_sentiment_label(avg_sentiment)
        }

    def _analyze_keyword_context(self, text: str, keyword: str) -> float:
        """Analyze sentiment in the context around a specific keyword."""
        # Find all occurrences of the keyword
        index = text.find(keyword)
        if index == -1:
            return 0.0

        # Extract context (50 chars before and after)
        start = max(0, index - 50)
        end = min(len(text), index + len(keyword) + 50)
        context = text[start:end]

        # Simple sentiment scoring based on context
        positive_words = ['good', 'great', 'excellent', 'love', 'perfect', 'amazing', 'best']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'poor']

        pos_score = sum(1 for word in positive_words if word in context)
        neg_score = sum(1 for word in negative_words if word in context)

        if pos_score + neg_score == 0:
            return 0.0

        return (pos_score - neg_score) / (pos_score + neg_score)

    def _detect_sentiment_modifiers(self, text: str) -> Dict[str, int]:
        """Detect sentiment intensity modifiers."""
        pos_mods = sum(1 for mod in self.positive_modifiers if mod in text)
        neg_mods = sum(1 for mod in self.negative_modifiers if mod in text)

        return {
            'positive_modifiers': pos_mods,
            'negative_modifiers': neg_mods,
            'intensity_score': (pos_mods - neg_mods) * 0.1
        }

    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to human-readable label."""
        if score > 0.5:
            return 'very_positive'
        elif score > 0.2:
            return 'positive'
        elif score > -0.2:
            return 'neutral'
        elif score > -0.5:
            return 'negative'
        else:
            return 'very_negative'


class TrendDetector:
    """Detect trends and patterns in content and pain points."""

    def detect_emerging_trends(self, campaign: Campaign, days: int = 30) -> List[Dict[str, Any]]:
        """
        Detect emerging trends in campaign data.

        Args:
            campaign: Campaign to analyze
            days: Number of days to look back

        Returns:
            List of detected trends with metadata
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        # Get recent content
        recent_content = ProcessedContent.objects.filter(
            raw_content__campaign=campaign,
            created_at__gte=cutoff_date
        ).values('keywords', 'created_at', 'sentiment_score')

        if not recent_content:
            return []

        # Analyze keyword frequency over time
        keyword_timeline = defaultdict(list)
        for content in recent_content:
            if content['keywords']:
                for keyword in content['keywords']:
                    keyword_timeline[keyword].append({
                        'date': content['created_at'],
                        'sentiment': content['sentiment_score'] or 0
                    })

        # Detect trending keywords (increasing frequency)
        trends = []
        for keyword, occurrences in keyword_timeline.items():
            if len(occurrences) < 3:  # Need minimum data points
                continue

            # Sort by date
            sorted_occurrences = sorted(occurrences, key=lambda x: x['date'])

            # Calculate trend (simple linear approximation)
            trend_score = self._calculate_trend_score(sorted_occurrences)

            if trend_score > 0.3:  # Significant upward trend
                avg_sentiment = statistics.mean([o['sentiment'] for o in occurrences])

                trends.append({
                    'keyword': keyword,
                    'trend_score': round(trend_score, 3),
                    'mention_count': len(occurrences),
                    'average_sentiment': round(avg_sentiment, 3),
                    'trend_direction': 'increasing',
                    'significance': 'high' if trend_score > 0.6 else 'medium'
                })

        # Sort by trend score
        return sorted(trends, key=lambda x: x['trend_score'], reverse=True)[:10]

    def _calculate_trend_score(self, occurrences: List[Dict]) -> float:
        """Calculate trend score based on frequency over time."""
        if len(occurrences) < 2:
            return 0.0

        # Split into first half and second half
        midpoint = len(occurrences) // 2
        first_half = occurrences[:midpoint]
        second_half = occurrences[midpoint:]

        # Compare frequencies
        first_freq = len(first_half)
        second_freq = len(second_half)

        if first_freq == 0:
            return 1.0 if second_freq > 0 else 0.0

        # Calculate percentage increase
        increase_ratio = (second_freq - first_freq) / first_freq

        # Normalize to 0-1 range
        return min(max(increase_ratio, 0), 1)

    def detect_pain_point_trends(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """Detect trends in pain points over time."""
        pain_points = PainPoint.objects.filter(
            campaign=campaign
        ).annotate(
            recent_mentions=Count('id')
        ).values('keyword', 'mention_count', 'growth_percentage', 'heat_level', 'sentiment_score')

        trending_pain_points = []

        for pp in pain_points:
            if pp['growth_percentage'] > 20:  # Growing by more than 20%
                trending_pain_points.append({
                    'keyword': pp['keyword'],
                    'mention_count': pp['mention_count'],
                    'growth_percentage': pp['growth_percentage'],
                    'heat_level': pp['heat_level'],
                    'sentiment_score': pp['sentiment_score'],
                    'trend': 'escalating' if pp['growth_percentage'] > 50 else 'growing',
                    'urgency': 'high' if pp['heat_level'] >= 4 else 'medium'
                })

        return sorted(trending_pain_points, key=lambda x: x['growth_percentage'], reverse=True)


class CompetitiveIntelligence:
    """Analyze competitive landscape and competitor mentions."""

    def analyze_competitor_landscape(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Analyze competitive landscape for a campaign.

        Returns:
            Dict containing competitor analysis and market insights
        """
        # Get competitor mentions from content
        competitor_data = defaultdict(lambda: {
            'mention_count': 0,
            'sentiment_scores': [],
            'contexts': []
        })

        # Analyze content for competitor mentions
        campaign_keywords = campaign.keywords.split(',') if campaign.keywords else []
        brand_name = campaign.brands.first().name if campaign.brands.exists() else campaign.name

        recent_content = ProcessedContent.objects.filter(
            raw_content__campaign=campaign
        ).select_related('raw_content')[:100]

        for content in recent_content:
            # Look for competitor comparison patterns
            competitors_found = self._extract_competitor_mentions(
                content.cleaned_content,
                brand_name
            )

            for competitor in competitors_found:
                competitor_data[competitor]['mention_count'] += 1
                if content.sentiment_score:
                    competitor_data[competitor]['sentiment_scores'].append(content.sentiment_score)
                competitor_data[competitor]['contexts'].append(content.cleaned_content[:200])

        # Calculate competitive metrics
        competitive_analysis = {
            'total_competitors_mentioned': len(competitor_data),
            'competitors': []
        }

        for competitor, data in competitor_data.items():
            if data['mention_count'] >= 2:  # Minimum threshold
                avg_sentiment = statistics.mean(data['sentiment_scores']) if data['sentiment_scores'] else 0

                competitive_analysis['competitors'].append({
                    'name': competitor,
                    'mention_count': data['mention_count'],
                    'average_sentiment': round(avg_sentiment, 3),
                    'relative_strength': self._calculate_competitive_strength(
                        data['mention_count'],
                        avg_sentiment
                    ),
                    'sample_contexts': data['contexts'][:3]
                })

        # Sort by mention count
        competitive_analysis['competitors'] = sorted(
            competitive_analysis['competitors'],
            key=lambda x: x['mention_count'],
            reverse=True
        )

        return competitive_analysis

    def _extract_competitor_mentions(self, text: str, brand_name: str) -> List[str]:
        """Extract potential competitor mentions from text."""
        import re

        competitors = []

        # Look for comparison patterns
        patterns = [
            rf'({brand_name}|(\w+))\s+vs\.?\s+(\w+)',
            rf'compared\s+to\s+(\w+)',
            rf'better\s+than\s+(\w+)',
            rf'instead\s+of\s+(\w+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                potential_competitor = match if isinstance(match, str) else match[-1]
                if (potential_competitor and
                    potential_competitor.lower() != brand_name.lower() and
                    len(potential_competitor) > 2):
                    competitors.append(potential_competitor.title())

        return list(set(competitors))

    def _calculate_competitive_strength(self, mentions: int, sentiment: float) -> str:
        """Calculate competitive strength indicator."""
        strength_score = mentions * (1 + sentiment)

        if strength_score > 10:
            return 'strong'
        elif strength_score > 5:
            return 'moderate'
        else:
            return 'weak'


class InfluencerAnalyzer:
    """Identify and analyze influencers in the community."""

    def identify_influencers(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """
        Identify key influencers for a campaign.

        Returns:
            List of influencers with influence metrics
        """
        # Get threads related to campaign
        campaign_threads = Thread.objects.filter(
            community__thread__content__icontains=campaign.name
        ).distinct().values('author', 'echo_score', 'reply_count', 'view_count')

        # Aggregate by author
        author_metrics = defaultdict(lambda: {
            'thread_count': 0,
            'total_echo_score': 0,
            'total_replies': 0,
            'total_views': 0
        })

        for thread in campaign_threads:
            author = thread['author']
            if author and author != 'unknown':
                author_metrics[author]['thread_count'] += 1
                author_metrics[author]['total_echo_score'] += thread['echo_score'] or 0
                author_metrics[author]['total_replies'] += thread['reply_count'] or 0
                author_metrics[author]['total_views'] += thread['view_count'] or 0

        # Calculate influence scores
        influencers = []

        for author, metrics in author_metrics.items():
            if metrics['thread_count'] >= 2:  # Minimum activity threshold
                avg_echo_score = metrics['total_echo_score'] / metrics['thread_count']
                avg_engagement = (metrics['total_replies'] + metrics['total_views'] / 10) / metrics['thread_count']

                influence_score = (avg_echo_score * 0.4 + avg_engagement * 0.3 + metrics['thread_count'] * 0.3)

                influencers.append({
                    'username': author,
                    'influence_score': round(influence_score, 2),
                    'thread_count': metrics['thread_count'],
                    'average_echo_score': round(avg_echo_score, 2),
                    'total_engagement': metrics['total_replies'] + metrics['total_views'],
                    'influence_tier': self._get_influence_tier(influence_score)
                })

        # Sort by influence score
        return sorted(influencers, key=lambda x: x['influence_score'], reverse=True)[:20]

    def _get_influence_tier(self, score: float) -> str:
        """Categorize influence level."""
        if score > 50:
            return 'macro_influencer'
        elif score > 20:
            return 'micro_influencer'
        elif score > 10:
            return 'emerging_influencer'
        else:
            return 'regular_contributor'


class InsightGenerator:
    """Generate comprehensive, actionable insights from analysis."""

    def __init__(self):
        self.sentiment_analyzer = AdvancedSentimentAnalyzer()
        self.trend_detector = TrendDetector()
        self.competitive_intel = CompetitiveIntelligence()
        self.influencer_analyzer = InfluencerAnalyzer()

    def generate_comprehensive_insights(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """
        Generate comprehensive insights for a campaign.

        Returns:
            List of insights with type, priority, and actionable recommendations
        """
        all_insights = []

        # Generate sentiment insights
        sentiment_insights = self._generate_sentiment_insights(campaign)
        all_insights.extend(sentiment_insights)

        # Generate trend insights
        trend_insights = self._generate_trend_insights(campaign)
        all_insights.extend(trend_insights)

        # Generate competitive insights
        competitive_insights = self._generate_competitive_insights(campaign)
        all_insights.extend(competitive_insights)

        # Generate influencer insights
        influencer_insights = self._generate_influencer_insights(campaign)
        all_insights.extend(influencer_insights)

        # Score and prioritize insights
        scored_insights = self._score_and_prioritize(all_insights)

        return scored_insights[:15]  # Return top 15 insights

    def _generate_sentiment_insights(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """Generate insights from sentiment analysis."""
        insights = []

        recent_content = ProcessedContent.objects.filter(
            raw_content__campaign=campaign,
            created_at__gte=timezone.now() - timedelta(days=7)
        )

        if not recent_content.exists():
            return insights

        sentiments = [c.sentiment_score for c in recent_content if c.sentiment_score is not None]

        if sentiments:
            avg_sentiment = statistics.mean(sentiments)
            sentiment_std = statistics.stdev(sentiments) if len(sentiments) > 1 else 0

            if avg_sentiment < -0.3:
                insights.append({
                    'type': 'sentiment',
                    'title': f'Negative Sentiment Alert for {campaign.name}',
                    'description': f'Recent analysis shows predominantly negative sentiment (avg: {avg_sentiment:.2f}) across {len(sentiments)} posts. Immediate attention recommended.',
                    'confidence': min(abs(avg_sentiment), 1.0),
                    'priority': 0.9,
                    'tags': ['sentiment', 'negative', 'urgent'],
                    'recommended_actions': [
                        'Investigate specific pain points causing negative sentiment',
                        'Engage with community to address concerns',
                        'Review product/service quality issues'
                    ],
                    'metadata': {
                        'avg_sentiment': avg_sentiment,
                        'sentiment_std': sentiment_std,
                        'sample_size': len(sentiments)
                    }
                })
            elif avg_sentiment > 0.3:
                insights.append({
                    'type': 'sentiment',
                    'title': f'Positive Sentiment Momentum for {campaign.name}',
                    'description': f'Strong positive sentiment detected (avg: {avg_sentiment:.2f}). Opportunity to amplify positive feedback.',
                    'confidence': min(avg_sentiment, 1.0),
                    'priority': 0.7,
                    'tags': ['sentiment', 'positive', 'opportunity'],
                    'recommended_actions': [
                        'Identify and engage with satisfied customers',
                        'Collect testimonials and success stories',
                        'Leverage positive sentiment in marketing'
                    ],
                    'metadata': {
                        'avg_sentiment': avg_sentiment,
                        'sample_size': len(sentiments)
                    }
                })

        return insights

    def _generate_trend_insights(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """Generate insights from trend analysis."""
        insights = []

        trends = self.trend_detector.detect_emerging_trends(campaign)

        for trend in trends[:3]:  # Top 3 trends
            insights.append({
                'type': 'trend',
                'title': f'Emerging Trend: {trend["keyword"].title()}',
                'description': f'Detected significant increase in discussions about {trend["keyword"]} (trend score: {trend["trend_score"]:.2f}, {trend["mention_count"]} mentions)',
                'confidence': trend['trend_score'],
                'priority': 0.75 if trend['significance'] == 'high' else 0.6,
                'tags': ['trend', 'emerging', trend['significance']],
                'recommended_actions': [
                    f'Monitor {trend["keyword"]} discussions closely',
                    'Analyze underlying causes of trend',
                    'Prepare response strategy if negative'
                ],
                'metadata': trend
            })

        return insights

    def _generate_competitive_insights(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """Generate competitive intelligence insights."""
        insights = []

        competitive_analysis = self.competitive_intel.analyze_competitor_landscape(campaign)

        if competitive_analysis['total_competitors_mentioned'] > 0:
            top_competitors = competitive_analysis['competitors'][:3]

            for competitor in top_competitors:
                insights.append({
                    'type': 'competitive',
                    'title': f'Competitor Mention: {competitor["name"]}',
                    'description': f'{competitor["name"]} mentioned {competitor["mention_count"]} times in comparative discussions (avg sentiment: {competitor["average_sentiment"]:.2f})',
                    'confidence': min(competitor['mention_count'] / 10, 1.0),
                    'priority': 0.65,
                    'tags': ['competitive', 'market_intelligence'],
                    'recommended_actions': [
                        f'Analyze {competitor["name"]}\'s strengths and weaknesses',
                        'Identify differentiation opportunities',
                        'Monitor competitive positioning'
                    ],
                    'metadata': competitor
                })

        return insights

    def _generate_influencer_insights(self, campaign: Campaign) -> List[Dict[str, Any]]:
        """Generate influencer-related insights."""
        insights = []

        influencers = self.influencer_analyzer.identify_influencers(campaign)

        if influencers:
            top_influencers = influencers[:3]

            insights.append({
                'type': 'influencer',
                'title': f'Key Influencers Identified for {campaign.name}',
                'description': f'Found {len(top_influencers)} key influencers with significant community impact. Top influencer: {top_influencers[0]["username"]} (score: {top_influencers[0]["influence_score"]})',
                'confidence': 0.8,
                'priority': 0.7,
                'tags': ['influencer', 'engagement', 'community'],
                'recommended_actions': [
                    'Engage with identified influencers',
                    'Build relationships with key community voices',
                    'Consider influencer partnership opportunities'
                ],
                'metadata': {
                    'top_influencers': top_influencers
                }
            })

        return insights

    def _score_and_prioritize(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and prioritize insights based on multiple factors."""
        for insight in insights:
            # Calculate composite score
            priority = insight.get('priority', 0.5)
            confidence = insight.get('confidence', 0.5)

            # Weight: priority 60%, confidence 40%
            composite_score = (priority * 0.6 + confidence * 0.4)

            insight['composite_score'] = round(composite_score, 3)

        # Sort by composite score
        return sorted(insights, key=lambda x: x['composite_score'], reverse=True)


# Global analyzer instance
advanced_analyzer = InsightGenerator()

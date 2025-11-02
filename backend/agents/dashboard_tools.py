"""
Dashboard Analytics Tools for Chatbot Agent.

This module provides specialized tools for querying dashboard analytics data:
- Brand KPIs and campaign budgets
- Community metrics and echo scores
- Influencer analytics and sentiment
- Pain point trends and severity
- Campaign performance and ROI
- Temporal trends (7d/30d/90d)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone

from common.models import (
    Brand, Campaign, ProcessedContent, Community,
    Influencer, PainPoint, Insight
)

logger = logging.getLogger(__name__)


class BrandAnalyticsTool:
    """
    Query brand-level analytics including KPIs, campaigns, and budgets.

    Use this tool when queries mention:
    - Brand performance, brand metrics, brand KPIs
    - Campaign counts, active campaigns
    - Budget allocation, spending
    - Brand-specific insights
    """

    name = "brand_analytics"
    description = (
        "Query brand-level analytics including KPIs (total posts, sentiment, echo score), "
        "campaign counts, budget allocation, and recent activity. "
        "Use for questions about specific brands or overall brand performance."
    )

    def run(
        self,
        brand_id: Optional[str] = None,
        brand_name: Optional[str] = None,
        include_campaigns: bool = True,
        include_kpis: bool = True,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute brand analytics query.

        Args:
            brand_id: Specific brand ID to query
            brand_name: Brand name to search for (case-insensitive)
            include_campaigns: Include campaign statistics
            include_kpis: Include KPI metrics
            limit: Maximum number of brands to return

        Returns:
            Dictionary with brand analytics data
        """
        try:
            # Build queryset
            queryset = Brand.objects.all()

            if brand_id:
                queryset = queryset.filter(id=brand_id)
            elif brand_name:
                queryset = queryset.filter(name__icontains=brand_name)

            brands = list(queryset[:limit])

            if not brands:
                return {
                    "success": False,
                    "message": "No brands found matching criteria",
                    "brands": []
                }

            results = []

            for brand in brands:
                brand_data = {
                    "id": str(brand.id),
                    "name": brand.name,
                    "created_at": brand.created_at.isoformat() if brand.created_at else None
                }

                if include_kpis:
                    # Get content statistics
                    content_stats = ProcessedContent.objects.filter(
                        brand=brand
                    ).aggregate(
                        total_posts=Count('id'),
                        avg_sentiment=Avg('sentiment_score'),
                        avg_echo_score=Avg('echo_score')
                    )

                    # Get insight count
                    insight_count = Insight.objects.filter(brand=brand).count()

                    # Get pain point count
                    pain_point_count = PainPoint.objects.filter(brand=brand).count()

                    brand_data["kpis"] = {
                        "total_posts": content_stats["total_posts"] or 0,
                        "avg_sentiment": round(content_stats["avg_sentiment"] or 0.0, 2),
                        "avg_echo_score": round(content_stats["avg_echo_score"] or 0.0, 2),
                        "total_insights": insight_count,
                        "total_pain_points": pain_point_count
                    }

                if include_campaigns:
                    # Get campaign statistics
                    campaigns = Campaign.objects.filter(brand=brand)

                    active_campaigns = campaigns.filter(status='active').count()
                    total_budget = campaigns.aggregate(
                        total=Sum('budget')
                    )['total'] or 0.0

                    recent_campaigns = list(
                        campaigns.order_by('-created_at')[:5].values(
                            'id', 'name', 'status', 'budget', 'created_at'
                        )
                    )

                    brand_data["campaigns"] = {
                        "total_campaigns": campaigns.count(),
                        "active_campaigns": active_campaigns,
                        "total_budget": float(total_budget),
                        "recent_campaigns": [
                            {
                                "id": str(c["id"]),
                                "name": c["name"],
                                "status": c["status"],
                                "budget": float(c["budget"]) if c["budget"] else 0.0,
                                "created_at": c["created_at"].isoformat() if c["created_at"] else None
                            }
                            for c in recent_campaigns
                        ]
                    }

                results.append(brand_data)

            return {
                "success": True,
                "count": len(results),
                "brands": results
            }

        except Exception as e:
            logger.error(f"BrandAnalyticsTool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "brands": []
            }


class CommunityQueryTool:
    """
    Query community data including echo scores, activity levels, and member counts.

    Use this tool when queries mention:
    - Communities, community detection
    - Echo chambers, echo scores
    - Community activity, engagement
    - Top communities by size or activity
    """

    name = "community_query"
    description = (
        "Query community analytics including echo scores, activity levels, member counts, "
        "and top communities. Use for questions about echo chambers, community dynamics, "
        "or community-based analysis."
    )

    async def run(
        self,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        min_echo_score: Optional[float] = None,
        sort_by: str = "echo_score",  # echo_score, activity_level, member_count
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute community query.

        Args:
            brand_id: Filter by brand
            campaign_id: Filter by campaign
            min_echo_score: Minimum echo score threshold
            sort_by: Field to sort by (echo_score, activity_level, member_count)
            limit: Maximum number of communities to return

        Returns:
            Dictionary with community data
        """
        try:
            queryset = Community.objects.all()

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if min_echo_score is not None:
                queryset = queryset.filter(echo_score__gte=min_echo_score)

            # Sort
            sort_field_map = {
                "echo_score": "-echo_score",
                "activity_level": "-activity_level",
                "member_count": "-member_count"
            }
            sort_field = sort_field_map.get(sort_by, "-echo_score")
            queryset = queryset.order_by(sort_field)

            communities = list(queryset[:limit].values(
                'id', 'name', 'echo_score', 'activity_level',
                'member_count', 'brand_id', 'campaign_id',
                'dominant_sentiment', 'created_at'
            ))

            if not communities:
                return {
                    "success": False,
                    "message": "No communities found matching criteria",
                    "communities": []
                }

            # Calculate statistics
            all_communities = queryset.aggregate(
                total=Count('id'),
                avg_echo_score=Avg('echo_score'),
                avg_activity=Avg('activity_level'),
                total_members=Sum('member_count')
            )

            results = [
                {
                    "id": str(c["id"]),
                    "name": c["name"],
                    "echo_score": round(c["echo_score"] or 0.0, 2),
                    "activity_level": round(c["activity_level"] or 0.0, 2),
                    "member_count": c["member_count"] or 0,
                    "dominant_sentiment": c["dominant_sentiment"],
                    "brand_id": str(c["brand_id"]) if c["brand_id"] else None,
                    "campaign_id": str(c["campaign_id"]) if c["campaign_id"] else None,
                    "created_at": c["created_at"].isoformat() if c["created_at"] else None
                }
                for c in communities
            ]

            return {
                "success": True,
                "count": len(results),
                "statistics": {
                    "total_communities": all_communities["total"],
                    "avg_echo_score": round(all_communities["avg_echo_score"] or 0.0, 2),
                    "avg_activity": round(all_communities["avg_activity"] or 0.0, 2),
                    "total_members": all_communities["total_members"] or 0
                },
                "communities": results
            }

        except Exception as e:
            logger.error(f"CommunityQueryTool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "communities": []
            }


class InfluencerQueryTool:
    """
    Query influencer data including sentiment, reach, advocacy scores.

    Use this tool when queries mention:
    - Influencers, key voices, thought leaders
    - Reach, followers, influence metrics
    - Advocacy scores, sentiment
    - Top influencers by reach or advocacy
    """

    name = "influencer_query"
    description = (
        "Query influencer analytics including sentiment, reach, advocacy scores, "
        "and top influencers. Use for questions about key voices, thought leaders, "
        "or influencer-based analysis."
    )

    async def run(
        self,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        min_advocacy_score: Optional[float] = None,
        sentiment: Optional[str] = None,  # positive, neutral, negative
        sort_by: str = "advocacy_score",  # advocacy_score, reach, sentiment_score
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute influencer query.

        Args:
            brand_id: Filter by brand
            campaign_id: Filter by campaign
            min_advocacy_score: Minimum advocacy score threshold
            sentiment: Filter by sentiment (positive, neutral, negative)
            sort_by: Field to sort by
            limit: Maximum number of influencers to return

        Returns:
            Dictionary with influencer data
        """
        try:
            queryset = Influencer.objects.all()

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if min_advocacy_score is not None:
                queryset = queryset.filter(advocacy_score__gte=min_advocacy_score)

            if sentiment:
                queryset = queryset.filter(sentiment=sentiment)

            # Sort
            sort_field_map = {
                "advocacy_score": "-advocacy_score",
                "reach": "-reach",
                "sentiment_score": "-sentiment_score"
            }
            sort_field = sort_field_map.get(sort_by, "-advocacy_score")
            queryset = queryset.order_by(sort_field)

            influencers = list(queryset[:limit].values(
                'id', 'name', 'advocacy_score', 'reach',
                'sentiment', 'sentiment_score', 'brand_id',
                'campaign_id', 'created_at'
            ))

            if not influencers:
                return {
                    "success": False,
                    "message": "No influencers found matching criteria",
                    "influencers": []
                }

            # Calculate statistics
            all_influencers = queryset.aggregate(
                total=Count('id'),
                avg_advocacy=Avg('advocacy_score'),
                avg_sentiment=Avg('sentiment_score'),
                total_reach=Sum('reach')
            )

            results = [
                {
                    "id": str(i["id"]),
                    "name": i["name"],
                    "advocacy_score": round(i["advocacy_score"] or 0.0, 2),
                    "reach": i["reach"] or 0,
                    "sentiment": i["sentiment"],
                    "sentiment_score": round(i["sentiment_score"] or 0.0, 2),
                    "brand_id": str(i["brand_id"]) if i["brand_id"] else None,
                    "campaign_id": str(i["campaign_id"]) if i["campaign_id"] else None,
                    "created_at": i["created_at"].isoformat() if i["created_at"] else None
                }
                for i in influencers
            ]

            return {
                "success": True,
                "count": len(results),
                "statistics": {
                    "total_influencers": all_influencers["total"],
                    "avg_advocacy_score": round(all_influencers["avg_advocacy"] or 0.0, 2),
                    "avg_sentiment_score": round(all_influencers["avg_sentiment"] or 0.0, 2),
                    "total_reach": all_influencers["total_reach"] or 0
                },
                "influencers": results
            }

        except Exception as e:
            logger.error(f"InfluencerQueryTool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "influencers": []
            }


class PainPointAnalysisTool:
    """
    Query pain point data including growth trends, severity, and frequency.

    Use this tool when queries mention:
    - Pain points, customer problems, complaints
    - Growth trends, emerging issues
    - Severity, urgency, critical issues
    - Pain point frequency or mentions
    """

    name = "pain_point_analysis"
    description = (
        "Query pain point analytics including growth trends, severity, frequency, "
        "and top pain points. Use for questions about customer problems, complaints, "
        "or emerging issues."
    )

    async def run(
        self,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        min_severity: Optional[int] = None,
        growth_trend: Optional[str] = None,  # rising, stable, declining
        sort_by: str = "mentions",  # mentions, severity, growth_rate
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute pain point analysis query.

        Args:
            brand_id: Filter by brand
            campaign_id: Filter by campaign
            min_severity: Minimum severity level (1-5)
            growth_trend: Filter by growth trend
            sort_by: Field to sort by
            limit: Maximum number of pain points to return

        Returns:
            Dictionary with pain point data
        """
        try:
            queryset = PainPoint.objects.all()

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if min_severity is not None:
                queryset = queryset.filter(severity__gte=min_severity)

            if growth_trend:
                queryset = queryset.filter(growth_trend=growth_trend)

            # Sort
            sort_field_map = {
                "mentions": "-mentions",
                "severity": "-severity",
                "growth_rate": "-growth_rate"
            }
            sort_field = sort_field_map.get(sort_by, "-mentions")
            queryset = queryset.order_by(sort_field)

            pain_points = list(queryset[:limit].values(
                'id', 'keyword', 'category', 'mentions',
                'severity', 'growth_rate', 'growth_trend',
                'sentiment_distribution', 'example_content',
                'brand_id', 'campaign_id', 'created_at'
            ))

            if not pain_points:
                return {
                    "success": False,
                    "message": "No pain points found matching criteria",
                    "pain_points": []
                }

            # Calculate statistics
            all_pain_points = queryset.aggregate(
                total=Count('id'),
                avg_severity=Avg('severity'),
                total_mentions=Sum('mentions'),
                avg_growth_rate=Avg('growth_rate')
            )

            # Count by trend
            trend_distribution = queryset.values('growth_trend').annotate(
                count=Count('id')
            )

            results = [
                {
                    "id": str(p["id"]),
                    "keyword": p["keyword"],
                    "category": p["category"],
                    "mentions": p["mentions"] or 0,
                    "severity": p["severity"] or 0,
                    "growth_rate": round(p["growth_rate"] or 0.0, 2),
                    "growth_trend": p["growth_trend"],
                    "sentiment_distribution": p["sentiment_distribution"],
                    "example_content": p["example_content"][:200] if p["example_content"] else None,
                    "brand_id": str(p["brand_id"]) if p["brand_id"] else None,
                    "campaign_id": str(p["campaign_id"]) if p["campaign_id"] else None,
                    "created_at": p["created_at"].isoformat() if p["created_at"] else None
                }
                for p in pain_points
            ]

            return {
                "success": True,
                "count": len(results),
                "statistics": {
                    "total_pain_points": all_pain_points["total"],
                    "avg_severity": round(all_pain_points["avg_severity"] or 0.0, 2),
                    "total_mentions": all_pain_points["total_mentions"] or 0,
                    "avg_growth_rate": round(all_pain_points["avg_growth_rate"] or 0.0, 2),
                    "trend_distribution": {
                        t["growth_trend"]: t["count"]
                        for t in trend_distribution
                        if t["growth_trend"]
                    }
                },
                "pain_points": results
            }

        except Exception as e:
            logger.error(f"PainPointAnalysisTool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "pain_points": []
            }


class CampaignAnalyticsTool:
    """
    Query campaign performance including ROI, engagement, and content metrics.

    Use this tool when queries mention:
    - Campaign performance, campaign analytics
    - ROI, return on investment
    - Campaign engagement, reach
    - Campaign status, active campaigns
    """

    name = "campaign_analytics"
    description = (
        "Query campaign performance analytics including status, budget, content count, "
        "sentiment, and engagement metrics. Use for questions about campaign effectiveness, "
        "ROI, or campaign-specific analysis."
    )

    async def run(
        self,
        campaign_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        status: Optional[str] = None,  # active, completed, paused
        min_budget: Optional[float] = None,
        sort_by: str = "created_at",  # created_at, budget, content_count
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute campaign analytics query.

        Args:
            campaign_id: Specific campaign ID
            brand_id: Filter by brand
            status: Filter by status
            min_budget: Minimum budget threshold
            sort_by: Field to sort by
            limit: Maximum number of campaigns to return

        Returns:
            Dictionary with campaign analytics
        """
        try:
            queryset = Campaign.objects.all()

            if campaign_id:
                queryset = queryset.filter(id=campaign_id)

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if status:
                queryset = queryset.filter(status=status)

            if min_budget is not None:
                queryset = queryset.filter(budget__gte=min_budget)

            # Sort
            sort_field_map = {
                "created_at": "-created_at",
                "budget": "-budget",
                "content_count": "-id"  # Will calculate separately
            }
            sort_field = sort_field_map.get(sort_by, "-created_at")
            queryset = queryset.order_by(sort_field)

            campaigns = list(queryset[:limit])

            if not campaigns:
                return {
                    "success": False,
                    "message": "No campaigns found matching criteria",
                    "campaigns": []
                }

            results = []

            for campaign in campaigns:
                # Get content statistics
                content_stats = ProcessedContent.objects.filter(
                    campaign=campaign
                ).aggregate(
                    total_content=Count('id'),
                    avg_sentiment=Avg('sentiment_score'),
                    avg_echo_score=Avg('echo_score')
                )

                # Get insight count
                insight_count = Insight.objects.filter(campaign=campaign).count()

                # Get community count
                community_count = Community.objects.filter(campaign=campaign).count()

                # Get influencer count
                influencer_count = Influencer.objects.filter(campaign=campaign).count()

                campaign_data = {
                    "id": str(campaign.id),
                    "name": campaign.name,
                    "status": campaign.status,
                    "budget": float(campaign.budget) if campaign.budget else 0.0,
                    "brand_id": str(campaign.brand_id) if campaign.brand_id else None,
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                    "metadata": campaign.metadata,
                    "metrics": {
                        "content_count": content_stats["total_content"] or 0,
                        "avg_sentiment": round(content_stats["avg_sentiment"] or 0.0, 2),
                        "avg_echo_score": round(content_stats["avg_echo_score"] or 0.0, 2),
                        "insight_count": insight_count,
                        "community_count": community_count,
                        "influencer_count": influencer_count
                    }
                }

                results.append(campaign_data)

            # Overall statistics
            all_campaigns = queryset.aggregate(
                total=Count('id'),
                total_budget=Sum('budget'),
                avg_budget=Avg('budget')
            )

            return {
                "success": True,
                "count": len(results),
                "statistics": {
                    "total_campaigns": all_campaigns["total"],
                    "total_budget": float(all_campaigns["total_budget"] or 0.0),
                    "avg_budget": float(all_campaigns["avg_budget"] or 0.0)
                },
                "campaigns": results
            }

        except Exception as e:
            logger.error(f"CampaignAnalyticsTool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "campaigns": []
            }


class TrendAnalysisTool:
    """
    Query temporal trends including 7-day, 30-day, and 90-day analytics.

    Use this tool when queries mention:
    - Trends over time, temporal analysis
    - Recent activity, last week/month/quarter
    - Growth patterns, changes over time
    - Time-based comparisons
    """

    name = "trend_analysis"
    description = (
        "Query temporal trends and time-based analytics for 7-day, 30-day, and 90-day periods. "
        "Use for questions about trends over time, recent activity, or temporal patterns."
    )

    async def run(
        self,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        period: str = "30d",  # 7d, 30d, 90d
        metric_type: str = "all"  # all, content, sentiment, communities, pain_points
    ) -> Dict[str, Any]:
        """
        Execute trend analysis query.

        Args:
            brand_id: Filter by brand
            campaign_id: Filter by campaign
            period: Time period (7d, 30d, 90d)
            metric_type: Type of metrics to analyze

        Returns:
            Dictionary with trend data
        """
        try:
            # Calculate date range
            period_map = {
                "7d": 7,
                "30d": 30,
                "90d": 90
            }
            days = period_map.get(period, 30)
            start_date = timezone.now() - timedelta(days=days)

            # Base filters
            filters = {"created_at__gte": start_date}
            if brand_id:
                filters["brand_id"] = brand_id
            if campaign_id:
                filters["campaign_id"] = campaign_id

            results = {
                "period": period,
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": timezone.now().isoformat()
            }

            # Content trends
            if metric_type in ["all", "content"]:
                content_by_day = ProcessedContent.objects.filter(
                    **filters
                ).extra(
                    select={'day': 'date(created_at)'}
                ).values('day').annotate(
                    count=Count('id'),
                    avg_sentiment=Avg('sentiment_score'),
                    avg_echo_score=Avg('echo_score')
                ).order_by('day')

                results["content_trends"] = [
                    {
                        "date": item["day"].isoformat() if item["day"] else None,
                        "count": item["count"],
                        "avg_sentiment": round(item["avg_sentiment"] or 0.0, 2),
                        "avg_echo_score": round(item["avg_echo_score"] or 0.0, 2)
                    }
                    for item in content_by_day
                ]

                # Total stats
                total_content = ProcessedContent.objects.filter(**filters).aggregate(
                    total=Count('id'),
                    avg_sentiment=Avg('sentiment_score'),
                    avg_echo_score=Avg('echo_score')
                )

                results["content_summary"] = {
                    "total_posts": total_content["total"] or 0,
                    "avg_sentiment": round(total_content["avg_sentiment"] or 0.0, 2),
                    "avg_echo_score": round(total_content["avg_echo_score"] or 0.0, 2)
                }

            # Sentiment trends
            if metric_type in ["all", "sentiment"]:
                sentiment_dist = ProcessedContent.objects.filter(
                    **filters
                ).values('sentiment').annotate(
                    count=Count('id')
                )

                results["sentiment_distribution"] = {
                    item["sentiment"]: item["count"]
                    for item in sentiment_dist
                    if item["sentiment"]
                }

            # Community trends
            if metric_type in ["all", "communities"]:
                community_stats = Community.objects.filter(**filters).aggregate(
                    total=Count('id'),
                    avg_echo_score=Avg('echo_score'),
                    avg_activity=Avg('activity_level'),
                    total_members=Sum('member_count')
                )

                results["community_summary"] = {
                    "total_communities": community_stats["total"] or 0,
                    "avg_echo_score": round(community_stats["avg_echo_score"] or 0.0, 2),
                    "avg_activity": round(community_stats["avg_activity"] or 0.0, 2),
                    "total_members": community_stats["total_members"] or 0
                }

            # Pain point trends
            if metric_type in ["all", "pain_points"]:
                pain_point_stats = PainPoint.objects.filter(**filters).aggregate(
                    total=Count('id'),
                    avg_severity=Avg('severity'),
                    total_mentions=Sum('mentions')
                )

                # Trending pain points
                trending_pain_points = PainPoint.objects.filter(
                    **filters,
                    growth_trend='rising'
                ).order_by('-growth_rate')[:5].values(
                    'keyword', 'mentions', 'severity', 'growth_rate'
                )

                results["pain_point_summary"] = {
                    "total_pain_points": pain_point_stats["total"] or 0,
                    "avg_severity": round(pain_point_stats["avg_severity"] or 0.0, 2),
                    "total_mentions": pain_point_stats["total_mentions"] or 0,
                    "trending": [
                        {
                            "keyword": p["keyword"],
                            "mentions": p["mentions"] or 0,
                            "severity": p["severity"] or 0,
                            "growth_rate": round(p["growth_rate"] or 0.0, 2)
                        }
                        for p in trending_pain_points
                    ]
                }

            return {
                "success": True,
                "trends": results
            }

        except Exception as e:
            logger.error(f"TrendAnalysisTool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "trends": {}
            }


# Tool instances for easy import
brand_analytics_tool = BrandAnalyticsTool()
community_query_tool = CommunityQueryTool()
influencer_query_tool = InfluencerQueryTool()
pain_point_analysis_tool = PainPointAnalysisTool()
campaign_analytics_tool = CampaignAnalyticsTool()
trend_analysis_tool = TrendAnalysisTool()

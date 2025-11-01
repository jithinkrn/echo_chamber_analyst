"""
Celery Tasks for EchoChamber Analyst

This module contains all the Celery tasks for background processing including:
- Periodic scout data collection
- Dashboard data cleanup
- Daily insight generation
- Campaign performance monitoring
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from celery import shared_task, Task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Avg, Q

from common.models import (
    Campaign, Brand, Source, Community, PainPoint,
    Thread, Insight, ProcessedContent, DashboardMetrics
)
from .orchestrator import workflow_orchestrator
from .state import CampaignContext, create_initial_state
from .scout_data_collection import collect_real_brand_data
from .nodes import _store_real_dashboard_data
from .campaign_completion import check_and_complete_campaigns  # Import to register with Celery

logger = get_task_logger(__name__)


class CallbackTask(Task):
    """Base task with callbacks for monitoring"""

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {self.name} [{task_id}] succeeded")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {self.name} [{task_id}] failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(f"Task {self.name} [{task_id}] retrying: {exc}")


@shared_task(base=CallbackTask, bind=True, max_retries=3, default_retry_delay=300)
def scout_reddit_task(self, campaign_id: Optional[int] = None, config: Optional[Dict] = None):
    """
    Periodic task to collect Reddit data for all active campaigns or a specific campaign.

    Args:
        campaign_id: Optional specific campaign ID to process
        config: Optional scout configuration dict

    Returns:
        Dict with collection statistics
    """
    logger.info(f"🔍 Starting scout Reddit task - Campaign ID: {campaign_id or 'all active'}")

    try:
        # Determine which campaigns to process
        if campaign_id:
            campaigns = Campaign.objects.filter(id=campaign_id, status='active')
        else:
            campaigns = Campaign.objects.filter(
                status='active',
                brand__isnull=False
            ).distinct()

        if not campaigns.exists():
            logger.warning("No active campaigns found for scout task")
            return {"status": "skipped", "reason": "no_active_campaigns"}

        results = {
            "total_campaigns": campaigns.count(),
            "successful": 0,
            "failed": 0,
            "total_data_collected": {
                "communities": 0,
                "threads": 0,
                "pain_points": 0
            },
            "campaign_results": []
        }

        # Process each campaign
        for campaign in campaigns:
            try:
                logger.info(f"Processing campaign: {campaign.name} (ID: {campaign.id})")

                # Get brand information
                brand = campaign.brand
                if not brand:
                    logger.warning(f"Campaign {campaign.id} has no associated brand")
                    continue

                # Prepare scout configuration with full brand context
                scout_config = config or {
                    # Brand information for accurate searches
                    'focus': 'brand_monitoring',
                    'collection_months': 6,
                    'brand_description': brand.description if brand.description else '',
                    'brand_website': brand.website if brand.website else '',
                    'industry': brand.industry if brand.industry else 'general',
                    
                    # Search configuration
                    'search_depth': 'comprehensive',
                    'include_sentiment': True,
                    'include_competitors': True,
                    'focus_areas': ['pain_points', 'feedback', 'sentiment'],

                    # Token optimization
                    'max_communities': 10,
                    'threads_per_community': 20,
                    'relevance_threshold': 3,
                    'max_threads_to_analyze': 50,

                    # Source diversity
                    'max_forum_sites': 5,
                    'max_queries_per_forum': 3,
                    'max_results_per_forum': 4,
                    'min_threads_per_source': 5,
                    'ensure_source_diversity': True,

                    # Pain point tracking
                    'track_pain_points_by_week': True,
                    'pain_point_weeks': 4,

                    # LLM optimization
                    'use_batch_llm_processing': True,
                    'batch_size': 10,
                    'use_summary_based_insights': True,
                }

                # Collect real brand data
                brand_keywords = [kw.strip() for kw in campaign.keywords.split(',')] if campaign.keywords else [brand.name]

                # Use asyncio to run the async function
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                collected_data = loop.run_until_complete(
                    collect_real_brand_data(brand.name, brand_keywords, scout_config)
                )

                loop.close()

                # Store LLM-discovered sources in database for frontend access
                from common.models import Source
                from django.utils import timezone

                if 'discovered_sources' in collected_data:
                    discovered = collected_data['discovered_sources']
                    focus = scout_config.get('focus', 'comprehensive')
                    industry = scout_config.get('industry', 'general')

                    # Store Reddit communities
                    for community_name in discovered.get('reddit_communities', []):
                        try:
                            Source.objects.get_or_create(
                                name=f"r/{community_name}",
                                source_type='reddit',
                                url=f"https://reddit.com/r/{community_name}",
                                defaults={
                                    'description': f'LLM-discovered Reddit community for {brand.name} ({focus})',
                                    'is_default': False,
                                    'is_active': True,
                                    'category': 'llm_discovered',
                                    'config': {
                                        'discovered_by': 'llm',
                                        'brand': brand.name,
                                        'focus': focus,
                                        'industry': industry,
                                        'reasoning': discovered.get('reasoning', ''),
                                        'discovered_at': discovered.get('discovered_at', timezone.now().isoformat()),
                                        'cache_hit': discovered.get('cache_hit', False),
                                        'is_fallback': discovered.get('is_fallback', False)
                                    },
                                    'last_accessed': timezone.now()
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Failed to store Reddit source r/{community_name}: {e}")

                    # Store forums
                    for forum_domain in discovered.get('forums', []):
                        try:
                            Source.objects.get_or_create(
                                name=forum_domain,
                                source_type='forum',
                                url=f"https://{forum_domain}",
                                defaults={
                                    'description': f'LLM-discovered forum for {brand.name} ({focus})',
                                    'is_default': False,
                                    'is_active': True,
                                    'category': 'llm_discovered',
                                    'config': {
                                        'discovered_by': 'llm',
                                        'brand': brand.name,
                                        'focus': focus,
                                        'industry': industry,
                                        'reasoning': discovered.get('reasoning', ''),
                                        'discovered_at': discovered.get('discovered_at', timezone.now().isoformat()),
                                        'cache_hit': discovered.get('cache_hit', False),
                                        'is_fallback': discovered.get('is_fallback', False)
                                    },
                                    'last_accessed': timezone.now()
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Failed to store forum source {forum_domain}: {e}")

                    logger.info(f"📝 Stored {len(discovered.get('reddit_communities', []))} Reddit communities and {len(discovered.get('forums', []))} forums")

                # Store data in database
                # Create a simple campaign context object for storage
                class SimpleCampaign:
                    def __init__(self, campaign_obj):
                        self.id = campaign_obj.id
                        self.campaign_id = str(campaign_obj.id)

                simple_campaign = SimpleCampaign(campaign)

                # Call storage function directly (handles async LLM calls internally)
                _store_real_dashboard_data(collected_data, simple_campaign, brand.name)

                # Track results
                results["successful"] += 1
                results["total_data_collected"]["communities"] += len(collected_data.get("communities", []))
                results["total_data_collected"]["threads"] += len(collected_data.get("threads", []))
                results["total_data_collected"]["pain_points"] += len(collected_data.get("pain_points", []))

                campaign_result = {
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "brand_name": brand.name,
                    "communities_found": len(collected_data.get("communities", [])),
                    "threads_collected": len(collected_data.get("threads", [])),
                    "pain_points_identified": len(collected_data.get("pain_points", [])),
                    "status": "success"
                }
                results["campaign_results"].append(campaign_result)

                logger.info(f"✅ Successfully collected data for campaign {campaign.name}")

            except Exception as e:
                logger.error(f"Failed to process campaign {campaign.id}: {e}", exc_info=True)
                results["failed"] += 1
                results["campaign_results"].append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "status": "failed",
                    "error": str(e)
                })

        logger.info(f"✅ Scout task completed - Successful: {results['successful']}, Failed: {results['failed']}")
        return results

    except Exception as e:
        logger.error(f"Scout Reddit task failed: {e}", exc_info=True)
        # Retry the task
        raise self.retry(exc=e)


@shared_task(base=CallbackTask, bind=True, max_retries=2)
def cleanup_old_data_task(self, days_to_keep: int = 90):
    """
    Periodic task to clean up old data from the database.

    Args:
        days_to_keep: Number of days to keep data (default: 90)

    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"🧹 Starting data cleanup task - keeping last {days_to_keep} days")

    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        results = {
            "cutoff_date": cutoff_date.isoformat(),
            "deleted_counts": {},
            "status": "success"
        }

        with transaction.atomic():
            # Clean up old threads
            threads_deleted = Thread.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            results["deleted_counts"]["threads"] = threads_deleted[0] if threads_deleted else 0

            # Clean up old processed content (keep if associated with active campaigns)
            old_content = ProcessedContent.objects.filter(
                created_at__lt=cutoff_date
            ).exclude(
                raw_content__campaign__is_active=True
            )
            content_deleted = old_content.delete()
            results["deleted_counts"]["processed_content"] = content_deleted[0] if content_deleted else 0

            # Clean up orphaned communities (no threads in last period)
            orphaned_communities = Community.objects.annotate(
                thread_count=Count('thread', filter=Q(thread__created_at__gte=cutoff_date))
            ).filter(thread_count=0)
            communities_deleted = orphaned_communities.delete()
            results["deleted_counts"]["communities"] = communities_deleted[0] if communities_deleted else 0

            # Archive old insights (mark as archived instead of deleting)
            old_insights = Insight.objects.filter(
                created_at__lt=cutoff_date,
                is_archived=False
            )
            insights_archived = old_insights.update(is_archived=True)
            results["deleted_counts"]["insights_archived"] = insights_archived

            logger.info(f"✅ Cleanup completed: {results['deleted_counts']}")

        return results

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}", exc_info=True)
        results["status"] = "failed"
        results["error"] = str(e)
        raise self.retry(exc=e)


@shared_task(base=CallbackTask, bind=True, max_retries=3)
def generate_daily_insights_task(self, campaign_id: Optional[int] = None):
    """
    Periodic task to generate daily insights for campaigns.

    Args:
        campaign_id: Optional specific campaign ID to process

    Returns:
        Dict with insight generation statistics
    """
    logger.info(f"💡 Starting daily insights generation - Campaign ID: {campaign_id or 'all active'}")

    try:
        # Determine which campaigns to process
        if campaign_id:
            campaigns = Campaign.objects.filter(id=campaign_id, status='active')
        else:
            campaigns = Campaign.objects.filter(status='active')

        if not campaigns.exists():
            logger.warning("No active campaigns found for insight generation")
            return {"status": "skipped", "reason": "no_active_campaigns"}

        results = {
            "total_campaigns": campaigns.count(),
            "successful": 0,
            "failed": 0,
            "total_insights_generated": 0,
            "campaign_results": []
        }

        for campaign in campaigns:
            try:
                logger.info(f"Generating insights for campaign: {campaign.name}")

                # Get recent content for analysis
                recent_cutoff = timezone.now() - timedelta(hours=24)
                recent_content = ProcessedContent.objects.filter(
                    raw_content__campaign=campaign,
                    created_at__gte=recent_cutoff
                ).select_related('raw_content').order_by('-created_at')[:50]

                if not recent_content.exists():
                    logger.info(f"No recent content found for campaign {campaign.name}")
                    continue

                # Analyze sentiment trends
                sentiment_insights = _generate_sentiment_insights(campaign, recent_content)

                # Analyze pain point trends
                pain_point_insights = _generate_pain_point_insights(campaign)

                # Analyze engagement trends
                engagement_insights = _generate_engagement_insights(campaign)

                # Combine all insights
                all_insights = sentiment_insights + pain_point_insights + engagement_insights

                # Store insights in database
                for insight_data in all_insights:
                    Insight.objects.create(
                        campaign=campaign,
                        insight_type=insight_data["type"],
                        title=insight_data["title"],
                        description=insight_data["description"],
                        confidence_score=insight_data.get("confidence", 0.7),
                        priority_score=insight_data.get("priority", 0.5),
                        tags=insight_data.get("tags", []),
                        metadata=insight_data.get("metadata", {})
                    )

                results["successful"] += 1
                results["total_insights_generated"] += len(all_insights)
                results["campaign_results"].append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "insights_generated": len(all_insights),
                    "status": "success"
                })

                logger.info(f"✅ Generated {len(all_insights)} insights for campaign {campaign.name}")

            except Exception as e:
                logger.error(f"Failed to generate insights for campaign {campaign.id}: {e}", exc_info=True)
                results["failed"] += 1
                results["campaign_results"].append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "status": "failed",
                    "error": str(e)
                })

        logger.info(f"✅ Insights generation completed - Generated: {results['total_insights_generated']}")
        return results

    except Exception as e:
        logger.error(f"Daily insights task failed: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(base=CallbackTask)
def update_dashboard_metrics_task(campaign_id: Optional[int] = None):
    """
    Task to update dashboard metrics for real-time display.

    Args:
        campaign_id: Optional specific campaign ID to update

    Returns:
        Dict with update statistics
    """
    logger.info(f"📊 Updating dashboard metrics - Campaign ID: {campaign_id or 'all'}")

    try:
        if campaign_id:
            campaigns = Campaign.objects.filter(id=campaign_id)
        else:
            campaigns = Campaign.objects.filter(status='active')

        results = {
            "campaigns_updated": 0,
            "metrics_calculated": []
        }

        for campaign in campaigns:
            # Calculate metrics
            total_content = ProcessedContent.objects.filter(
                raw_content__campaign=campaign
            ).count()

            total_insights = Insight.objects.filter(
                campaign=campaign,
                is_archived=False
            ).count()

            avg_sentiment = ProcessedContent.objects.filter(
                raw_content__campaign=campaign
            ).aggregate(avg_sentiment=Avg('sentiment_score'))['avg_sentiment'] or 0.0

            pain_points_count = PainPoint.objects.filter(
                campaign=campaign
            ).count()

            # Update or create dashboard metrics
            DashboardMetrics.objects.update_or_create(
                campaign=campaign,
                defaults={
                    'total_content_processed': total_content,
                    'total_insights_generated': total_insights,
                    'average_sentiment_score': round(avg_sentiment, 2),
                    'pain_points_identified': pain_points_count,
                    'last_updated': timezone.now()
                }
            )

            results["campaigns_updated"] += 1
            results["metrics_calculated"].append({
                "campaign_id": campaign.id,
                "total_content": total_content,
                "total_insights": total_insights,
                "avg_sentiment": round(avg_sentiment, 2)
            })

        logger.info(f"✅ Dashboard metrics updated for {results['campaigns_updated']} campaigns")
        return results

    except Exception as e:
        logger.error(f"Dashboard metrics update failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


@shared_task(base=CallbackTask, bind=True)
def run_campaign_analysis_workflow(self, campaign_id: int, workflow_type: str = "content_analysis"):
    """
    Task to run a complete campaign analysis workflow using the orchestrator.

    Args:
        campaign_id: Campaign ID to analyze
        workflow_type: Type of workflow to run

    Returns:
        Dict with workflow results
    """
    logger.info(f"🚀 Starting workflow for campaign {campaign_id} - Type: {workflow_type}")

    try:
        campaign = Campaign.objects.get(id=campaign_id)

        # Create campaign context
        campaign_context = CampaignContext(
            campaign_id=str(campaign.id),
            name=campaign.name,
            keywords=campaign.keywords.split(',') if campaign.keywords else [],
            sources=[],
            budget_limit=campaign.budget_limit or 100.0,
            current_spend=0.0
        )

        # Execute workflow
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        final_state = loop.run_until_complete(
            workflow_orchestrator.execute_workflow(
                campaign=campaign_context,
                workflow_type=workflow_type
            )
        )

        loop.close()

        # Extract results
        results = {
            "campaign_id": campaign_id,
            "workflow_id": final_state.workflow_id,
            "status": final_state.task_status.value,
            "content_processed": len(final_state.processed_content),
            "insights_generated": len(final_state.insights),
            "total_cost": final_state.metrics.total_cost,
            "processing_time": final_state.metrics.processing_time,
            "errors": final_state.metrics.errors
        }

        logger.info(f"✅ Workflow completed for campaign {campaign_id}")
        return results

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return {"status": "failed", "error": "Campaign not found"}
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise self.retry(exc=e)


# Helper functions for insight generation

def _generate_sentiment_insights(campaign, recent_content) -> List[Dict]:
    """Generate insights from sentiment analysis"""
    insights = []

    # Calculate sentiment statistics
    sentiments = [c.sentiment_score for c in recent_content if c.sentiment_score is not None]

    if not sentiments:
        return insights

    avg_sentiment = sum(sentiments) / len(sentiments)
    positive_count = len([s for s in sentiments if s > 0.2])
    negative_count = len([s for s in sentiments if s < -0.2])

    # Generate sentiment trend insight
    if avg_sentiment > 0.3:
        insights.append({
            "type": "sentiment",
            "title": f"Positive Sentiment Trend for {campaign.name}",
            "description": f"Analysis of {len(sentiments)} recent posts shows a positive sentiment trend "
                          f"with {positive_count} positive mentions. Average sentiment score: {avg_sentiment:.2f}",
            "confidence": 0.8,
            "priority": 0.7,
            "tags": ["sentiment", "positive", "trend"],
            "metadata": {"avg_sentiment": avg_sentiment, "sample_size": len(sentiments)}
        })
    elif avg_sentiment < -0.3:
        insights.append({
            "type": "sentiment",
            "title": f"Negative Sentiment Alert for {campaign.name}",
            "description": f"Analysis shows concerning negative sentiment with {negative_count} negative mentions. "
                          f"Average sentiment score: {avg_sentiment:.2f}. Immediate attention recommended.",
            "confidence": 0.85,
            "priority": 0.9,
            "tags": ["sentiment", "negative", "alert"],
            "metadata": {"avg_sentiment": avg_sentiment, "sample_size": len(sentiments)}
        })

    return insights


def _generate_pain_point_insights(campaign) -> List[Dict]:
    """Generate insights from pain point analysis"""
    insights = []

    # Get top pain points
    top_pain_points = PainPoint.objects.filter(
        campaign=campaign
    ).order_by('-mention_count')[:5]

    if top_pain_points.exists():
        # Generate summary insight
        pain_point_list = ", ".join([pp.keyword for pp in top_pain_points[:3]])
        total_mentions = sum([pp.mention_count for pp in top_pain_points])

        insights.append({
            "type": "pain_point",
            "title": f"Top Pain Points Identified for {campaign.name}",
            "description": f"Analysis identified {top_pain_points.count()} major pain points with {total_mentions} total mentions. "
                          f"Key issues: {pain_point_list}",
            "confidence": 0.85,
            "priority": 0.8,
            "tags": ["pain_points", "customer_feedback"],
            "metadata": {
                "total_pain_points": top_pain_points.count(),
                "total_mentions": total_mentions
            }
        })

    return insights


def _generate_engagement_insights(campaign) -> List[Dict]:
    """Generate insights from engagement metrics"""
    insights = []

    # Get community engagement data
    communities = Community.objects.filter(
        thread__content__contains=campaign.name
    ).distinct().annotate(
        thread_count=Count('thread')
    ).order_by('-thread_count')[:3]

    if communities.exists():
        community_names = ", ".join([c.name for c in communities])
        total_threads = sum([c.thread_count for c in communities])

        insights.append({
            "type": "trend",
            "title": f"High Engagement Communities for {campaign.name}",
            "description": f"Found {total_threads} discussions across {communities.count()} active communities: {community_names}",
            "confidence": 0.75,
            "priority": 0.6,
            "tags": ["engagement", "communities", "trend"],
            "metadata": {
                "community_count": communities.count(),
                "total_discussions": total_threads
            }
        })

    return insights


@shared_task(base=CallbackTask, bind=True)
def check_and_execute_scheduled_campaigns(self):
    """
    Periodic task to check for campaigns that need to run based on their schedule.
    This task runs frequently (e.g., every minute) and executes campaigns whose
    next_run_at time has passed.

    Returns:
        Dict with execution statistics
    """
    logger.info("⏰ Checking for scheduled campaigns that need to run")

    try:
        now = timezone.now()

        # Find campaigns that need to run:
        # 1. Active status
        # 2. Schedule enabled
        # 3. Either never run before OR next_run_at has passed
        campaigns_to_run = Campaign.objects.filter(
            status='active',
            schedule_enabled=True
        ).filter(
            Q(next_run_at__isnull=True, last_run_at__isnull=True) |  # Never run
            Q(next_run_at__lte=now)  # Next run time has passed
        )

        if not campaigns_to_run.exists():
            logger.debug(f"No campaigns need to run at {now}")
            return {"status": "success", "campaigns_executed": 0, "message": "No campaigns ready to run"}

        results = {
            "campaigns_executed": 0,
            "campaigns_failed": 0,
            "campaign_details": []
        }

        for campaign in campaigns_to_run:
            try:
                logger.info(f"🚀 Executing scheduled campaign: {campaign.name} (ID: {campaign.id})")

                # Calculate next run time BEFORE executing
                next_run = now + timedelta(seconds=campaign.schedule_interval)

                # Update campaign run times
                campaign.last_run_at = now
                campaign.next_run_at = next_run
                campaign.save(update_fields=['last_run_at', 'next_run_at'])

                # Execute the campaign using the appropriate task based on campaign type
                if campaign.campaign_type == 'automatic':
                    # Brand Analytics campaign
                    scout_brand_analytics_task.delay(brand_id=campaign.brand_id)
                    logger.info(f"🔍 Launched Brand Analytics task for brand {campaign.brand_id}")
                else:
                    # Custom Campaign
                    scout_custom_campaign_task.delay(campaign_id=campaign.id)
                    logger.info(f"🔍 Launched Custom Campaign task for campaign {campaign.id}")

                results["campaigns_executed"] += 1
                results["campaign_details"].append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "executed_at": now.isoformat(),
                    "next_run_at": next_run.isoformat(),
                    "interval_seconds": campaign.schedule_interval,
                    "status": "executed"
                })

                logger.info(f"✅ Scheduled campaign {campaign.name} for execution. Next run: {next_run}")

            except Exception as e:
                logger.error(f"Failed to execute campaign {campaign.id}: {e}", exc_info=True)
                results["campaigns_failed"] += 1
                results["campaign_details"].append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "status": "failed",
                    "error": str(e)
                })

        logger.info(f"✅ Campaign check completed - Executed: {results['campaigns_executed']}, Failed: {results['campaigns_failed']}")
        return results

    except Exception as e:
        logger.error(f"Campaign scheduler task failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@shared_task(base=CallbackTask, bind=True, max_retries=3, default_retry_delay=300)
def scout_brand_analytics_task(self, brand_id: int):
    """
    Collect data for Brand Analytics (automatic campaign) ONLY.

    This runs on a schedule for continuous brand monitoring.
    Stores data linked to the brand's automatic campaign.

    Args:
        brand_id: ID of the brand to collect analytics for

    Returns:
        Dict with collection statistics
    """
    logger.info(f"🔍 Starting Brand Analytics data collection for brand {brand_id}")

    try:
        # Get automatic campaign for this brand
        automatic_campaign = Campaign.objects.filter(
            brand_id=brand_id,
            campaign_type='automatic',
            status='active'
        ).first()

        if not automatic_campaign:
            logger.warning(f"No automatic campaign found for brand {brand_id}")
            return {"status": "skipped", "reason": "no_automatic_campaign"}

        brand = automatic_campaign.brand
        logger.info(f"Processing automatic campaign: {automatic_campaign.name} (ID: {automatic_campaign.id})")

        # Prepare scout configuration for Brand Analytics with full brand context
        scout_config = {
            'search_depth': 'comprehensive',
            'focus': 'brand_monitoring',
            'collection_months': 6,
            'brand_description': brand.description if brand.description else '',
            'brand_website': brand.website if brand.website else '',
            'industry': brand.industry if brand.industry else 'general',
            'include_sentiment': True,
            'include_competitors': True,
            'focus_areas': ['pain_points', 'feedback', 'sentiment', 'communities']
        }

        # Collect real brand data
        brand_keywords = [kw.strip() for kw in brand.primary_keywords] if brand.primary_keywords else [brand.name]

        # Use asyncio to run the async function
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        collected_data = loop.run_until_complete(
            collect_real_brand_data(brand.name, brand_keywords, scout_config)
        )

        loop.close()

        # Store LLM-discovered sources
        if 'discovered_sources' in collected_data:
            discovered = collected_data['discovered_sources']
            focus = scout_config.get('focus', 'brand_monitoring')

            # Store Reddit communities
            for community_name in discovered.get('reddit_communities', []):
                try:
                    Source.objects.get_or_create(
                        name=f"r/{community_name}",
                        source_type='reddit',
                        url=f"https://reddit.com/r/{community_name}",
                        defaults={
                            'description': f'Brand Analytics - LLM-discovered Reddit community for {brand.name}',
                            'is_default': False,
                            'is_active': True,
                            'category': 'brand_analytics',
                            'config': {
                                'discovered_by': 'llm',
                                'brand': brand.name,
                                'focus': focus,
                                'campaign_type': 'automatic',
                                'discovered_at': discovered.get('discovered_at', timezone.now().isoformat()),
                            },
                            'last_accessed': timezone.now()
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to store Reddit source r/{community_name}: {e}")

        # Store data in database for Brand Analytics
        from .nodes import store_brand_analytics_data
        store_brand_analytics_data(collected_data, brand, automatic_campaign)

        logger.info(f"✅ Successfully collected Brand Analytics data for {brand.name}")
        logger.info(f"📊 Stored: {len(collected_data.get('communities', []))} communities, "
                   f"{len(collected_data.get('pain_points', []))} pain points, "
                   f"{len(collected_data.get('threads', []))} threads")

        return {
            "status": "success",
            "brand_id": brand_id,
            "brand_name": brand.name,
            "campaign_id": automatic_campaign.id,
            "campaign_type": "automatic",
            "data_collected": {
                "communities": len(collected_data.get("communities", [])),
                "threads": len(collected_data.get("threads", [])),
                "pain_points": len(collected_data.get("pain_points", []))
            }
        }

    except Exception as e:
        logger.error(f"Brand Analytics collection failed for brand {brand_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(base=CallbackTask, bind=True, max_retries=3, default_retry_delay=300)
def scout_custom_campaign_task(self, campaign_id: int):
    """
    Collect data for a specific Custom Campaign ONLY.

    This runs on user-defined schedule with custom parameters.
    Stores data linked to the specific custom campaign.

    Args:
        campaign_id: ID of the custom campaign to process

    Returns:
        Dict with collection statistics
    """
    logger.info(f"🔍 Starting Custom Campaign data collection for campaign {campaign_id}")

    try:
        # Get custom campaign
        campaign = Campaign.objects.filter(
            id=campaign_id,
            campaign_type='custom',
            status='active'
        ).first()

        if not campaign:
            logger.warning(f"No custom campaign found: {campaign_id}")
            return {"status": "skipped", "reason": "no_custom_campaign"}

        brand = campaign.brand
        if not brand:
            logger.warning(f"Campaign {campaign_id} has no associated brand")
            return {"status": "skipped", "reason": "no_brand"}

        logger.info(f"Processing custom campaign: {campaign.name} (ID: {campaign.id})")
        if campaign.description:
            logger.info(f"📋 Campaign Objectives: {campaign.description[:200]}")

        # Prepare scout configuration using campaign-specific parameters with full brand context
        scout_config = {
            'search_depth': 'comprehensive',
            'focus': 'custom_campaign',
            'collection_months': 6,
            'brand_description': brand.description if brand.description else '',
            'brand_website': brand.website if brand.website else '',
            'industry': brand.industry if brand.industry else 'general',
            'campaign_objectives': campaign.description if campaign.description else None,
            'sources': campaign.sources if campaign.sources else [],
            'exclude_keywords': campaign.exclude_keywords if campaign.exclude_keywords else [],
            'include_sentiment': True,
            'focus_areas': ['pain_points', 'feedback', 'sentiment', 'objectives']
        }

        # Collect data using campaign-specific keywords
        campaign_keywords = campaign.keywords if campaign.keywords else [brand.name]

        # Use asyncio to run the async function
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        collected_data = loop.run_until_complete(
            collect_real_brand_data(brand.name, campaign_keywords, scout_config)
        )

        loop.close()

        # Store LLM-discovered sources (marked as custom campaign sources)
        if 'discovered_sources' in collected_data:
            discovered = collected_data['discovered_sources']

            for community_name in discovered.get('reddit_communities', []):
                try:
                    Source.objects.get_or_create(
                        name=f"r/{community_name}",
                        source_type='reddit',
                        url=f"https://reddit.com/r/{community_name}",
                        defaults={
                            'description': f'Custom Campaign - LLM-discovered for campaign {campaign.name}',
                            'is_default': False,
                            'is_active': True,
                            'category': 'custom_campaign',
                            'config': {
                                'discovered_by': 'llm',
                                'brand': brand.name,
                                'campaign_id': str(campaign.id),
                                'campaign_type': 'custom',
                                'discovered_at': discovered.get('discovered_at', timezone.now().isoformat()),
                            },
                            'last_accessed': timezone.now()
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to store Reddit source r/{community_name}: {e}")

        # Store data in database for Custom Campaign
        from .nodes import store_custom_campaign_data
        store_custom_campaign_data(collected_data, brand, campaign)

        logger.info(f"✅ Successfully collected Custom Campaign data for {campaign.name}")
        logger.info(f"📊 Stored: {len(collected_data.get('communities', []))} communities, "
                   f"{len(collected_data.get('pain_points', []))} pain points, "
                   f"{len(collected_data.get('threads', []))} threads")

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "campaign_type": "custom",
            "brand_id": brand.id,
            "brand_name": brand.name,
            "data_collected": {
                "communities": len(collected_data.get("communities", [])),
                "threads": len(collected_data.get("threads", [])),
                "pain_points": len(collected_data.get("pain_points", []))
            }
        }

    except Exception as e:
        logger.error(f"Custom Campaign collection failed for campaign {campaign_id}: {e}", exc_info=True)
        raise self.retry(exc=e)

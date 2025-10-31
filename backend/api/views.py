"""
API views for EchoChamber Analyst - LangGraph Integration.

This module provides API endpoints that use LangGraph workflows
instead of the custom agent system, providing better orchestration,
monitoring, and compliance tracking.
"""
# REPLACE THE MESSY IMPORT SECTION (LINES 1-21) WITH:
import asyncio
import uuid
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# Model imports
from common.models import (
    Campaign, Brand, Community, PainPoint, Thread,
    Competitor, DashboardMetrics, Influencer, Source
)

# Agent imports
from agents.orchestrator import workflow_orchestrator
from agents.state import CampaignContext, create_chat_state
from agents.scout_data_collection import collect_real_brand_data

# LangChain imports
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint - LangGraph powered."""
    return Response({
        'message': 'EchoChamber Analyst API - LangGraph Edition',
        'version': '2.0.0',
        'framework': 'LangGraph with LangChain',
        'features': [
            'Sophisticated workflow orchestration',
            'LangSmith monitoring and observability',
            'Advanced retry mechanisms',
            'Compliance tracking and audit trails',
            'Parallel execution capabilities'
        ],
        'endpoints': {
            'chat': '/api/v1/chat/',
            'search': '/api/v1/search/',
            'campaign_summary': '/api/v1/campaigns/{campaign_id}/summary/',
            'content_analysis': '/api/v1/workflows/content-analysis/',
            'workflow_status': '/api/v1/workflows/{workflow_id}/status/',
            'admin': '/api/v1/admin/',
        },
        'monitoring': {
            'langsmith_enabled': True,
            'compliance_tracking': True,
            'error_recovery': True,
            'cost_tracking': True
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for AWS ECS/ALB health checks.
    Returns 200 OK if the service is healthy.
    """
    from django.db import connection

    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'echochamber-analyst',
        'version': '2.0.0'
    }

    # Check database connectivity
    try:
        connection.ensure_connection()
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = 'disconnected'
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
        return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Check Redis connectivity (optional)
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['redis'] = 'connected'
        else:
            health_status['redis'] = 'disconnected'
    except Exception as e:
        health_status['redis'] = 'disconnected'
        logger.warning(f"Redis health check failed: {e}")

    return Response(health_status, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat_query(request):
    """Handle chat queries through LangGraph chatbot workflow."""
    try:
        data = request.data
        query = data.get('query', '').strip()
        campaign_id = data.get('campaign_id')
        conversation_history = data.get('conversation_history', [])

        if not query:
            return Response(
                {'error': 'Query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Processing chat query: {query[:100]}...")

        # Validate campaign if provided
        campaign = None
        if campaign_id:
            try:
                campaign = Campaign.objects.get(id=campaign_id)
            except Campaign.DoesNotExist:
                return Response(
                    {'error': 'Campaign not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Convert conversation history to LangChain messages
        messages = []
        for msg in conversation_history:
            if isinstance(msg, dict):
                if msg.get('role') == 'user':
                    messages.append(HumanMessage(content=msg.get('content', '')))
                # Add AI messages if needed

        # Execute chat workflow using LangGraph
        final_state = asyncio.run(workflow_orchestrator.execute_chat_workflow(
            user_query=query,
            conversation_history=messages,
            campaign_id=campaign_id
        ))

        # Extract response from workflow state
        if hasattr(final_state, 'rag_context') and final_state.rag_context and 'response' in final_state.rag_context:
            response_content = final_state.rag_context['response']
            sources = final_state.rag_context.get('sources', [])
            search_results = final_state.rag_context.get('search_results', {})

            return Response({
                'response': response_content,
                'context_used': len(search_results.get('results', [])),
                'sources': sources,
                'tokens_used': final_state.metrics.total_tokens_used if hasattr(final_state, 'metrics') else 0,
                'cost': final_state.metrics.total_cost if hasattr(final_state, 'metrics') else 0,
                'workflow_id': final_state.workflow_id if hasattr(final_state, 'workflow_id') else 'unknown',
                'compliance_tracked': len(final_state.audit_trail) > 0 if hasattr(final_state, 'audit_trail') else False
            })
        elif isinstance(final_state, dict) and 'rag_context' in final_state and final_state['rag_context'] and 'response' in final_state['rag_context']:
            response_content = final_state['rag_context']['response']
            sources = final_state['rag_context'].get('sources', [])
            search_results = final_state['rag_context'].get('search_results', {})

            return Response({
                'response': response_content,
                'context_used': len(search_results.get('results', [])),
                'sources': sources,
                'tokens_used': final_state.get('metrics', {}).get('total_tokens_used', 0),
                'cost': final_state.get('metrics', {}).get('total_cost', 0),
                'workflow_id': final_state.get('workflow_id', 'unknown'),
                'compliance_tracked': len(final_state.get('audit_trail', [])) > 0
            })
        else:
            # Fallback response if workflow didn't complete properly
            return Response(
                {'error': 'Chat workflow completed but no response generated'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        return Response(
            {'error': f'Chat query failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def search_content(request):
    """Search content using LangGraph tools directly."""
    try:
        data = request.data
        query = data.get('query', '').strip()
        campaign_id = data.get('campaign_id')
        content_type = data.get('content_type', 'all')
        limit = min(data.get('limit', 20), 100)  # Cap at 100

        if not query:
            return Response(
                {'error': 'Query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Processing search query: {query[:100]}...")

        # Use LangGraph tools directly for search
        from agents.tools import LANGGRAPH_TOOLS
        search_tool = LANGGRAPH_TOOLS["content_search"]

        # Execute search using the tool
        search_result = asyncio.run(search_tool._arun(
            query=query,
            campaign_id=campaign_id,
            content_type=content_type if content_type != 'all' else None,
            limit=limit
        ))

        if search_result.get('success'):
            return Response({
                'results': search_result.get('results', []),
                'total_found': search_result.get('total_found', 0),
                'query': query,
                'search_metadata': {
                    'campaign_id': campaign_id,
                    'content_type': content_type,
                    'limit': limit
                }
            })
        else:
            return Response(
                {'error': search_result.get('error', 'Search failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return Response(
            {'error': f'Search failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def campaign_summary(request, campaign_id):
    """Generate a summary for a specific campaign using LangGraph tools."""
    try:
        # Validate campaign
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        logger.info(f"Generating summary for campaign: {campaign_id}")

        # Use LangGraph tools for campaign statistics
        from agents.tools import LANGGRAPH_TOOLS
        stats_tool = LANGGRAPH_TOOLS["get_campaign_stats"]

        # Get campaign statistics
        stats_result = asyncio.run(stats_tool._arun(campaign_id))

        if stats_result.get('success'):
            stats = stats_result

            # Create a comprehensive summary
            summary = {
                'campaign': stats['campaign'],
                'content_summary': stats['content'],
                'insights_summary': stats['insights'],
                'influencers_summary': stats['influencers'],
                'activity_summary': stats['activity'],
                'generated_at': timezone.now().isoformat(),
                'summary_type': 'campaign_overview'
            }

            # Generate AI-powered summary using chat workflow
            summary_query = f"Generate a comprehensive summary for campaign '{campaign.name}' based on the following metrics: {stats}"

            final_state = asyncio.run(workflow_orchestrator.execute_chat_workflow(
                user_query=summary_query,
                conversation_history=[],
                campaign_id=campaign_id
            ))

            if final_state.rag_context and 'response' in final_state.rag_context:
                summary['ai_summary'] = final_state.rag_context['response']
                summary['workflow_id'] = final_state.workflow_id
                summary['tokens_used'] = final_state.metrics.total_tokens_used
                summary['cost'] = final_state.metrics.total_cost

            return Response(summary)
        else:
            return Response(
                {'error': stats_result.get('error', 'Failed to get campaign statistics')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return Response(
            {'error': f'Summary generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def start_content_analysis(request):
    """Start a content analysis workflow using LangGraph."""
    try:
        data = request.data
        campaign_id = data.get('campaign_id')
        workflow_config = data.get('config', {})

        if not campaign_id:
            return Response(
                {'error': 'Campaign ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate campaign
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        logger.info(f"Starting content analysis workflow for campaign: {campaign_id}")

        # Create campaign context for LangGraph
        campaign_context = CampaignContext(
            campaign_id=campaign_id,
            name=campaign.name,
            keywords=campaign.keywords if hasattr(campaign, 'keywords') else [],
            sources=campaign.sources.values_list('url', flat=True) if hasattr(campaign, 'sources') else [],
            budget_limit=float(campaign.budget_limit) if hasattr(campaign, 'budget_limit') else 100.0,
            current_spend=float(campaign.current_spend) if hasattr(campaign, 'current_spend') else 0.0
        )

        # Execute content analysis workflow
        final_state = asyncio.run(workflow_orchestrator.execute_workflow(
            campaign=campaign_context,
            workflow_type="content_analysis",
            config=workflow_config
        ))

        # Extract results
        response_data = {
            'workflow_id': final_state.workflow_id,
            'status': final_state.task_status.value,
            'content_summary': final_state.get_content_summary(),
            'insights_generated': len(final_state.insights),
            'influencers_identified': len(final_state.influencers),
            'total_cost': final_state.metrics.total_cost,
            'total_tokens': final_state.metrics.total_tokens_used,
            'processing_time': final_state.metrics.processing_time,
            'errors': final_state.metrics.errors,
            'compliance_tracked': len(final_state.audit_trail) > 0
        }

        # Include insights if generated
        if final_state.insights:
            response_data['insights'] = [
                {
                    'id': insight.id,
                    'type': insight.insight_type.value,
                    'title': insight.title,
                    'description': insight.description,
                    'confidence': insight.confidence_score,
                    'priority': insight.priority_score
                }
                for insight in final_state.insights[:10]  # Limit to first 10
            ]

        return Response(response_data)

    except Exception as e:
        logger.error(f"Content analysis workflow failed: {e}")
        return Response(
            {'error': f'Content analysis failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def workflow_status(request, workflow_id):
    """Get the status of a LangGraph workflow."""
    try:
        logger.info(f"Getting status for workflow: {workflow_id}")

        # Get workflow status from orchestrator
        status_data = workflow_orchestrator.get_workflow_status(workflow_id)

        if status_data:
            return Response(status_data)
        else:
            return Response(
                {'error': 'Workflow not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        return Response(
            {'error': f'Status check failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Dashboard API Views

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_overview(request):
    """Main dashboard data endpoint."""
    try:
        from datetime import datetime, timedelta
        from django.db.models import Sum, Avg, Count, F
        from .serializers import (
            DashboardKPISerializer, CommunityHeatMapSerializer, 
            TopPainPointSerializer, CommunityWatchlistSerializer,
            InfluencerPulseSerializer
        )
        from common.models import Community, PainPoint, DashboardMetrics, Thread

        # Get filter parameters
        campaign_id = request.GET.get('campaign_id')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        brand = request.GET.get('brand', 'BreezyCool')
        
        # Default to last 7 days if no dates provided
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).date()
        if not date_to:
            date_to = datetime.now().date()
        
        logger.info(f"Dashboard overview request - Campaign: {campaign_id}, Date range: {date_from} to {date_to}")

        # Get KPI metrics
        kpi_data = get_dashboard_kpis(campaign_id, date_from, date_to)
        
        # Get community heatmap data
        heatmap_data = get_community_heatmap(campaign_id, date_from, date_to)
        
        # Get top growing pain points
        top_pain_points = get_top_pain_points(campaign_id, date_from, date_to)
        
        # Get community watchlist
        community_watchlist = get_community_watchlist(campaign_id, date_from, date_to)
        
        # Get influencer pulse
        influencer_pulse = get_influencer_pulse(campaign_id, date_from, date_to)
        
        dashboard_data = {
            "kpis": kpi_data,
            "heatmap": heatmap_data,
            "top_pain_points": top_pain_points,
            "community_watchlist": community_watchlist,
            "influencer_pulse": influencer_pulse,
            "filters": {
                "date_range": f"{date_from} - {date_to}",
                "brand": brand,
                "sources": ["Reddit", "Discord", "TikTok"]
            }
        }
        
        return Response(dashboard_data)
        
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        return Response(
            {'error': f'Dashboard data fetch failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def thread_detail(request, thread_id):
    """Thread detail modal data."""
    try:
        from .serializers import ThreadSerializer
        from common.models import Thread
        
        logger.info(f"Thread detail request for: {thread_id}")
        
        thread = Thread.objects.get(thread_id=thread_id)
        serializer = ThreadSerializer(thread)
        
        # Get related threads
        related_threads = Thread.objects.filter(
            community=thread.community,
            pain_points__in=thread.pain_points.all()
        ).exclude(id=thread.id)[:5]
        
        thread_data = serializer.data
        thread_data['related_threads'] = ThreadSerializer(related_threads, many=True).data
        
        return Response(thread_data)
        
    except Thread.DoesNotExist:
        return Response(
            {'error': 'Thread not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Thread detail error: {e}")
        return Response(
            {'error': f'Thread detail fetch failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_dashboard_kpis(campaign_id, date_from, date_to):
    """Calculate dashboard KPI metrics."""
    from django.db.models import Sum, Avg, Count
    from common.models import Campaign, Community, PainPoint, DashboardMetrics
    
    try:
        # Get metrics from DashboardMetrics table if available
        metrics = DashboardMetrics.objects.filter(
            date__range=[date_from, date_to]
        )
        
        if campaign_id:
            metrics = metrics.filter(campaign_id=campaign_id)
        
        aggregated = metrics.aggregate(
            total_tokens=Sum('llm_tokens_used'),
            total_cost=Sum('llm_cost_usd'),
            avg_positivity=Avg('positivity_ratio')
        )
        
        # Calculate other KPIs
        active_campaigns = Campaign.objects.filter(status='active').count()
        high_echo_communities = Community.objects.filter(echo_score__gte=7.0).count()
        
        pain_points_filter = {'created_at__date__range': [date_from, date_to]}
        if campaign_id:
            pain_points_filter['campaign_id'] = campaign_id
            
        new_pain_points_above_50 = PainPoint.objects.filter(
            growth_percentage__gte=50,
            **pain_points_filter
        ).count()
        
        return {
            "active_campaigns": active_campaigns,
            "high_echo_communities": high_echo_communities,
            "high_echo_change_percent": 0.0,  # TODO: Calculate from historical data
            "new_pain_points_above_50": new_pain_points_above_50,
            "new_pain_points_change": 0,  # TODO: Calculate actual change from previous period
            "positivity_ratio": round(aggregated['avg_positivity'] or 0.0, 1),
            "positivity_change_pp": 0.0,  # TODO: Calculate actual change from previous period
            "llm_tokens_used": (aggregated['total_tokens'] or 0) // 1000 if aggregated['total_tokens'] else 0,  # in thousands
            "llm_cost_usd": round(aggregated['total_cost'] or 0.0, 2)
        }
        
    except Exception as e:
        logger.error(f"KPI calculation error: {e}")
        # Return zeros if calculation fails
        return {
            "active_campaigns": 0,
            "high_echo_communities": 0,
            "high_echo_change_percent": 0.0,
            "new_pain_points_above_50": 0,
            "new_pain_points_change": 0,
            "positivity_ratio": 0.0,
            "positivity_change_pp": 0.0,
            "llm_tokens_used": 0,
            "llm_cost_usd": 0.0
        }


def get_community_heatmap(campaign_id, date_from, date_to):
    """Get community heatmap data."""
    from .serializers import CommunityHeatMapSerializer
    from common.models import Community
    
    try:
        communities_filter = {'last_analyzed__date__range': [date_from, date_to]}
        
        if campaign_id:
            communities_filter['thread__pain_points__campaign_id'] = campaign_id
            
        communities = Community.objects.filter(**communities_filter).distinct()[:10]
        
        if not communities.exists():
            # Return empty array if no communities found
            return []
        
        return CommunityHeatMapSerializer(communities, many=True).data
        
    except Exception as e:
        logger.error(f"Community heatmap error: {e}")
        return []


def get_top_pain_points(campaign_id, date_from, date_to):
    """Get top growing pain points."""
    from .serializers import TopPainPointSerializer
    from common.models import PainPoint
    
    try:
        pain_points_filter = {'created_at__date__range': [date_from, date_to]}
        if campaign_id:
            pain_points_filter['campaign_id'] = campaign_id
            
        pain_points = PainPoint.objects.filter(**pain_points_filter).order_by('-growth_percentage')[:10]
        
        if not pain_points.exists():
            # Return empty array if no pain points found
            return []
        
        return TopPainPointSerializer(pain_points, many=True).data
        
    except Exception as e:
        logger.error(f"Top pain points error: {e}")
        return []


def get_community_watchlist(campaign_id, date_from, date_to):
    """Get community watchlist data."""
    from common.models import Community, Thread
    from datetime import timedelta

    try:
        # Get communities ordered by echo score
        communities_filter = {'is_active': True, 'echo_score__gte': 5.0}
        if campaign_id:
            communities_filter['threads__campaign_id'] = campaign_id

        communities = Community.objects.filter(**communities_filter).distinct().order_by('-echo_score')[:5]

        if not communities.exists():
            return []

        watchlist_data = []
        for rank, community in enumerate(communities, 1):
            # Get recent thread count for this community
            recent_threads = Thread.objects.filter(
                community=community,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()

            # Get top influencer from this community
            top_influencer = community.influencers.order_by('-influence_score').first()

            watchlist_data.append({
                'rank': rank,
                'name': community.name,
                'platform': community.platform,
                'member_count': community.member_count,
                'echo_score': float(community.echo_score),
                'echo_change': float(community.echo_score_change or 0.0),
                'new_threads': recent_threads,
                'activity_score': float(community.activity_score),
                'threads_last_4_weeks': community.threads_last_4_weeks,
                'avg_engagement_rate': float(community.avg_engagement_rate),
                'key_influencer': top_influencer.handle if top_influencer else 'N/A'
            })

        return watchlist_data

    except Exception as e:
        logger.error(f"Community watchlist error: {e}")
        return []


def get_influencer_pulse(campaign_id, date_from, date_to):
    """Get influencer pulse data."""
    from .serializers import InfluencerPulseSerializer
    from common.models import Influencer
    
    try:
        influencers_filter = {'last_active__date__range': [date_from, date_to]}
        if campaign_id:
            influencers_filter['community__thread__pain_points__campaign_id'] = campaign_id
            
        influencers = Influencer.objects.filter(
            reach__lt=50000,  # <50k followers
            **influencers_filter
        ).distinct()[:10]
        
        if not influencers.exists():
            # Return empty array if no influencers found
            return []
        
        return InfluencerPulseSerializer(influencers, many=True).data
        
    except Exception as e:
        logger.error(f"Influencer pulse error: {e}")
        return []


# Brand Management API Views

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def brand_list(request):
    """List all brands or create a new brand."""
    from .serializers import BrandSerializer
    
    if request.method == 'GET':
        brands = Brand.objects.filter(is_active=True).order_by('name')
        serializer = BrandSerializer(brands, many=True)
        return Response({
            'results': serializer.data,
            'count': brands.count()
        })
    
    elif request.method == 'POST':
        serializer = BrandSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def brand_detail(request, brand_id):
    """Retrieve, update or delete a brand."""
    from .serializers import BrandSerializer
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return Response({'error': 'Brand not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BrandSerializer(brand)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BrandSerializer(brand, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Hard delete - actually remove from database
        brand_name = brand.name
        brand.delete()
        logger.info(f"🗑️ Deleted brand: {brand_name}")
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def competitor_list(request, brand_id):
    """List competitors for a brand or add a new competitor."""
    from .serializers import CompetitorSerializer
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return Response({'error': 'Brand not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        competitors = brand.competitors.filter(is_active=True)
        serializer = CompetitorSerializer(competitors, many=True)
        return Response({
            'results': serializer.data,
            'count': competitors.count()
        })
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['brand'] = brand_id
        serializer = CompetitorSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_overview_brand_filtered(request):
    """Dashboard overview filtered by brand."""
    brand_id = request.GET.get('brand_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not brand_id:
        return Response({'error': 'brand_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return Response({'error': 'Brand not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get brand-specific analytics
    data = {
        'brand': {
            'id': str(brand.id),
            'name': brand.name,
            'description': brand.description
        },
        'kpis': get_brand_dashboard_kpis(brand_id, date_from, date_to),
        'heatmap': get_brand_heatmap_data(brand_id, date_from, date_to),
        'top_pain_points': get_brand_top_pain_points(brand_id, date_from, date_to),
        'community_watchlist': get_brand_community_watchlist(brand_id),
        'influencer_pulse': get_brand_influencer_pulse(brand_id),
        'campaign_analytics': get_brand_campaign_analytics(brand_id, date_from, date_to)
    }
    
    return Response(data)


def get_brand_dashboard_kpis(brand_id, date_from, date_to):
    """Calculate KPI metrics for a specific brand - Brand Analytics ONLY."""
    from datetime import datetime, timedelta
    from django.db.models import Count, Avg, Sum
    from common.models import Campaign, Community, PainPoint, Thread

    # ✅ FIX: Get automatic campaign only (Brand Analytics)
    automatic_campaign = Campaign.objects.filter(
        brand_id=brand_id,
        campaign_type='automatic',
        status='active'
    ).first()

    if not automatic_campaign:
        # No automatic campaign - return zero metrics
        return {
            "active_campaigns": 0,
            "high_echo_communities": 0,
            "high_echo_change_percent": 0.0,
            "new_pain_points_above_50": 0,
            "new_pain_points_change": 0.0,
            "positivity_ratio": 0.0,
            "positivity_change_pp": 0.0,
            "llm_tokens_used": 0,
            "llm_cost_usd": 0.0
        }

    active_campaigns_count = 1  # Only the automatic campaign

    # ✅ FIX: Get brand-specific communities (Brand Analytics only)
    brand_communities = Community.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        echo_score__gte=7.0,
        is_active=True
    )
    high_echo_communities_count = brand_communities.count()

    # Calculate high echo communities change
    seven_days_ago = datetime.now() - timedelta(days=7)
    previous_high_echo = brand_communities.filter(
        last_analyzed__lt=seven_days_ago
    ).count()

    high_echo_change = 0
    if previous_high_echo > 0:
        high_echo_change = ((high_echo_communities_count - previous_high_echo) / previous_high_echo) * 100

    # ✅ FIX: Get brand-specific pain points (Brand Analytics only)
    brand_pain_points = PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        growth_percentage__gte=50,
        created_at__gte=seven_days_ago
    )
    high_growth_pain_points = brand_pain_points.count()

    # ✅ FIX: Calculate positivity ratio from brand-related threads (Brand Analytics only)
    brand_threads = Thread.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        analyzed_at__gte=seven_days_ago
    )

    if brand_threads.exists():
        avg_sentiment = brand_threads.aggregate(avg_sentiment=Avg('sentiment_score'))['avg_sentiment'] or 0
        positivity_ratio = max(0, min(100, (avg_sentiment + 1) * 50))
    else:
        positivity_ratio = 0.0

    # ✅ FIX: Get LLM token usage for Brand Analytics
    brand_token_usage = brand_threads.aggregate(total_tokens=Sum('token_count'))['total_tokens'] or 0
    brand_cost = brand_threads.aggregate(total_cost=Sum('processing_cost'))['total_cost'] or 0.0
    
    # Calculate change metrics by comparing current vs 24h ago
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

    # 1. Pain points change (current vs 24h ago) - Brand Analytics only
    previous_pain_points = PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        growth_percentage__gte=50,
        created_at__lt=twenty_four_hours_ago,
        created_at__gte=seven_days_ago
    ).count()

    pain_points_change = 0
    if previous_pain_points > 0:
        pain_points_change = ((high_growth_pain_points - previous_pain_points) / previous_pain_points) * 100
    elif high_growth_pain_points > 0:
        pain_points_change = 100  # If we had 0 before and now we have some, that's 100% increase

    # 2. Positivity ratio change (current vs 24h ago) - Brand Analytics only
    previous_threads = Thread.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        analyzed_at__gte=seven_days_ago,
        analyzed_at__lt=twenty_four_hours_ago
    )

    positivity_change_pp = 0.0
    if previous_threads.exists():
        prev_avg_sentiment = previous_threads.aggregate(avg_sentiment=Avg('sentiment_score'))['avg_sentiment'] or 0
        prev_positivity_ratio = max(0, min(100, (prev_avg_sentiment + 1) * 50))
        positivity_change_pp = positivity_ratio - prev_positivity_ratio  # Percentage point change

    return {
        "active_campaigns": active_campaigns_count,
        "high_echo_communities": high_echo_communities_count,
        "high_echo_change_percent": round(high_echo_change, 1),
        "new_pain_points_above_50": high_growth_pain_points,
        "new_pain_points_change": round(pain_points_change, 1),
        "positivity_ratio": round(positivity_ratio, 1),
        "positivity_change_pp": round(positivity_change_pp, 1),
        "llm_tokens_used": brand_token_usage // 1000 if brand_token_usage > 0 else 0,
        "llm_cost_usd": float(brand_cost)
    }


def get_brand_top_pain_points(brand_id, date_from, date_to):
    """Get top growing pain points for a specific brand - Brand Analytics ONLY."""
    from common.models import PainPoint

    # ✅ FIX: Get automatic campaign only (Brand Analytics)
    automatic_campaign = Campaign.objects.filter(
        brand_id=brand_id,
        campaign_type='automatic'
    ).first()

    if not automatic_campaign:
        return []

    # ✅ FIX: Get pain points for Brand Analytics only
    top_pain_points = PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        growth_percentage__gt=0  # Only growing pain points
    ).order_by('-growth_percentage')[:5]

    return [
        {
            'keyword': pp.keyword,
            'growth_percentage': float(pp.growth_percentage),
            'mention_count': pp.mention_count
        }
        for pp in top_pain_points
    ]


def get_brand_heatmap_data(brand_id, date_from, date_to):
    """Get dual heatmap data for a specific brand - Brand Analytics ONLY.

    Returns:
        dict with two heat map types:
        - community_pain_point_matrix: Communities (Y) × Pain Points (X) with heat = mention count
        - time_series_pain_points: Time periods (X) × Pain Points (Y) with heat = growth rate
    """
    from common.models import PainPoint, Community, Thread
    from datetime import timedelta
    from django.db.models import Count, Avg, Sum, Q
    from collections import defaultdict

    # ✅ FIX: Get automatic campaign only (Brand Analytics)
    automatic_campaign = Campaign.objects.filter(
        brand_id=brand_id,
        campaign_type='automatic'
    ).first()

    if not automatic_campaign:
        return {
            'community_pain_point_matrix': [],
            'time_series_pain_points': []
        }

    # ✅ FIX: Get pain points from Brand Analytics only
    all_brand_pain_points = PainPoint.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign
        # Removed heat_level filter to show all pain points
    ).select_related('community').order_by('-heat_level', '-growth_percentage')

    # === TYPE A: Community × Pain Point Matrix (heat = mention count) ===
    # UPDATED: Limit to top 4 communities by activity score for token efficiency
    community_matrix = []
    communities_processed = set()

    # ✅ FIX: Get communities that have pain points for this brand/campaign
    # First get community IDs that have pain points
    community_ids_with_pain_points = all_brand_pain_points.values_list('community_id', flat=True).distinct()

    # Then get the top 4 communities by activity
    top_communities = Community.objects.filter(
        id__in=community_ids_with_pain_points,
        brand_id=brand_id,
        campaign=automatic_campaign
    ).order_by('-activity_score', '-echo_score')[:4]

    for community in top_communities:
        # Get top pain points for this community
        community_pain_points = all_brand_pain_points.filter(
            community=community
        ).order_by('-mention_count', '-heat_level')[:5]

        if community_pain_points.exists():
            community_matrix.append({
                'community_name': community.name,
                'platform': community.platform,
                'echo_score': float(community.echo_score),
                'echo_score_delta': float(community.echo_score_delta),  # NEW: W-o-W delta
                'activity_score': float(community.activity_score),  # NEW: Activity metric
                'threads_4w': community.threads_last_4_weeks,  # NEW: Thread count
                'pain_points': [
                    {
                        'keyword': pp.keyword,
                        'mention_count': pp.mention_count,
                        'heat_level': pp.heat_level,
                        'sentiment_score': float(pp.sentiment_score),
                        'growth_percentage': float(pp.growth_percentage)
                    }
                    for pp in community_pain_points
                ]
            })

    # === TYPE B: Time Series Line Chart - Weekly Pain Points (4 weeks) ===
    time_series_matrix = []

    # Get all unique pain points across brand (top 5 most mentioned)
    # Use set to ensure uniqueness, then take first 5
    all_pain_point_keywords = list(set(
        all_brand_pain_points.values_list('keyword', flat=True)
    ))[:5]

    # Generate time buckets for last 4 weeks
    now = timezone.now()
    time_buckets = []
    for i in range(3, -1, -1):  # Last 4 weeks
        week_end = (now - timedelta(weeks=i)).replace(hour=23, minute=59, second=59, microsecond=999999)
        week_start = week_end - timedelta(days=6)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        time_buckets.append({
            'week_label': f'Week {4-i}',
            'date_range': f"{week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}",
            'start': week_start,
            'end': week_end
        })

    # Calculate total mentions across all pain points for each week
    total_mentions_series = []
    for bucket in time_buckets:
        total_count = Thread.objects.filter(
            campaign=automatic_campaign,
            brand_id=brand_id,
            published_at__gte=bucket['start'],
            published_at__lt=bucket['end']
        ).count()
        total_mentions_series.append({
            'label': bucket['week_label'],
            'date': bucket['date_range'],
            'total_mentions': total_count
        })

    # For each pain point, calculate mentions over time
    for keyword in all_pain_point_keywords:
        pain_point_time_data = {
            'keyword': keyword,
            'time_series': []
        }

        for bucket in time_buckets:
            # Count mentions in this time bucket across all communities
            mentions_count = Thread.objects.filter(
                campaign=automatic_campaign,
                brand_id=brand_id,
                published_at__gte=bucket['start'],
                published_at__lt=bucket['end'],
                content__icontains=keyword
            ).count()

            # Get average sentiment for this keyword in this time period
            avg_sentiment = Thread.objects.filter(
                campaign=automatic_campaign,
                brand_id=brand_id,
                published_at__gte=bucket['start'],
                published_at__lt=bucket['end'],
                content__icontains=keyword
            ).aggregate(avg_sentiment=Avg('sentiment_score'))['avg_sentiment'] or 0.0

            pain_point_time_data['time_series'].append({
                'label': bucket['week_label'],
                'date': bucket['date_range'],
                'mention_count': mentions_count,
                'sentiment_score': float(avg_sentiment),
                'heat_level': 3 if mentions_count > 5 else (2 if mentions_count > 2 else 1)
            })

        # Calculate weekly growth rate (week 3 vs week 4 for more meaningful comparison)
        # This shows if the issue is trending up or down recently
        time_series = pain_point_time_data['time_series']

        # Compare last week to second-to-last week
        if len(time_series) >= 2:
            previous_week = time_series[-2]['mention_count']
            current_week = time_series[-1]['mention_count']

            if previous_week > 0:
                growth_rate = ((current_week - previous_week) / previous_week * 100)
            elif current_week > 0:
                growth_rate = 100.0  # New mentions appeared
            else:
                growth_rate = 0.0
        else:
            growth_rate = 0.0

        pain_point_time_data['growth_rate'] = round(growth_rate, 1)
        pain_point_time_data['total_mentions'] = sum(tp['mention_count'] for tp in pain_point_time_data['time_series'])

        time_series_matrix.append(pain_point_time_data)

    # Sort time series by total mentions (most mentioned first)
    time_series_matrix = sorted(time_series_matrix, key=lambda x: x['total_mentions'], reverse=True)

    return {
        'community_pain_point_matrix': community_matrix,
        'time_series_pain_points': time_series_matrix,
        'total_mentions_series': total_mentions_series
    }


def get_brand_community_watchlist(brand_id):
    """Get community watchlist for a specific brand - Brand Analytics ONLY."""
    from common.models import Community, Thread
    from datetime import timedelta

    # ✅ FIX: Get automatic campaign only (Brand Analytics)
    automatic_campaign = Campaign.objects.filter(
        brand_id=brand_id,
        campaign_type='automatic'
    ).first()

    if not automatic_campaign:
        return []

    # ✅ FIX: Get communities for Brand Analytics only
    brand_communities = Community.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        is_active=True
        # Removed echo_score filter to show all communities
    ).distinct().order_by('-echo_score')[:5]

    watchlist_data = []
    for rank, community in enumerate(brand_communities, 1):
        # ✅ FIX: Get recent thread count for Brand Analytics only
        recent_threads = Thread.objects.filter(
            community=community,
            brand_id=brand_id,
            campaign=automatic_campaign,
            published_at__gte=timezone.now() - timedelta(days=28)  # Last 4 weeks
        ).count()

        # ✅ FIX: Get top influencer for Brand Analytics only
        top_influencer = community.influencers.filter(
            brand_id=brand_id,
            campaign=automatic_campaign
        ).order_by('-influence_score').first()
        
        watchlist_data.append({
            'rank': rank,
            'name': community.name,
            'platform': community.platform,
            'member_count': community.member_count,
            'echo_score': float(community.echo_score),
            'echo_change': float(community.echo_score_change),
            'new_threads': recent_threads,
            'activity_score': float(community.activity_score),
            'threads_last_4_weeks': community.threads_last_4_weeks,
            'avg_engagement_rate': float(community.avg_engagement_rate),
            'key_influencer': top_influencer.display_name if top_influencer else 'Unknown'
        })
    
    return watchlist_data


def get_brand_influencer_pulse(brand_id):
    """Get influencer pulse for a specific brand - Brand Analytics ONLY."""
    from common.models import Influencer

    # ✅ FIX: Get automatic campaign only (Brand Analytics)
    automatic_campaign = Campaign.objects.filter(
        brand_id=brand_id,
        campaign_type='automatic'
    ).first()

    if not automatic_campaign:
        return []

    # ✅ FIX: Get influencers for Brand Analytics only
    brand_influencers = Influencer.objects.filter(
        brand_id=brand_id,
        campaign=automatic_campaign,
        reach__lt=50000,  # Less than 50k followers
        reach__gt=0
    ).order_by('-engagement_rate')[:5]
    
    influencer_data = []
    for influencer in brand_influencers:
        # Get the topics they talk about
        topics_text = ', '.join(influencer.topics) if influencer.topics else influencer.content_topics[0] if influencer.content_topics else 'general discussion'
        
        influencer_data.append({
            'handle': influencer.username,
            'platform': influencer.source_type,
            'reach': influencer.reach,
            'engagement_rate': float(influencer.engagement_rate),
            'topics_text': topics_text[:50] + '...' if len(topics_text) > 50 else topics_text
        })
    
    return influencer_data


def get_brand_campaign_analytics(brand_id, date_from, date_to):
    """Get campaign analytics for a specific brand - Custom Campaigns ONLY."""
    from datetime import datetime, timedelta
    from django.db.models import Count, Avg, Sum

    # ✅ FIX: Get custom campaigns only (NOT automatic campaigns)
    custom_campaigns = Campaign.objects.filter(
        brand_id=brand_id,
        campaign_type='custom'  # Only custom campaigns
    )

    # Campaign performance metrics
    total_campaigns = custom_campaigns.count()
    active_campaigns = custom_campaigns.filter(status='active').count()
    completed_campaigns = custom_campaigns.filter(status='completed').count()

    # Budget analytics
    total_budget = custom_campaigns.aggregate(total=Sum('daily_budget'))['total'] or 0
    total_spent = custom_campaigns.aggregate(total=Sum('current_spend'))['total'] or 0

    # ✅ FIX: Get campaign insights from the latest CUSTOM campaign with insights
    campaign_insights = []
    campaign_data_summary = {}

    # Look for custom campaigns with insights in metadata (most recent first)
    campaigns_with_insights = custom_campaigns.filter(
        metadata__insights__isnull=False
    ).exclude(
        metadata__insights=[]
    ).order_by('-created_at')

    if campaigns_with_insights.exists():
        latest_campaign = campaigns_with_insights.first()
        if latest_campaign.metadata:
            campaign_insights = latest_campaign.metadata.get('insights', [])
            campaign_data_summary = latest_campaign.metadata.get('data_summary', {})

    return {
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'completed_campaigns': completed_campaigns,
        'paused_campaigns': custom_campaigns.filter(status='paused').count(),
        'total_budget': float(total_budget),
        'total_spent': float(total_spent),
        'budget_utilization': round((total_spent / total_budget * 100) if total_budget > 0 else 0, 1),
        'recent_campaigns': [],
        'insights': campaign_insights,  # Custom Campaign insights only
        'data_summary': campaign_data_summary  # Data summary for insights context
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def generate_ai_insights(request):
    """Generate AI-powered insights for a brand's dashboard data using LLM."""
    try:
        brand_id = request.query_params.get('brand_id')

        if not brand_id:
            return Response(
                {'error': 'brand_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get brand
        brand = Brand.objects.filter(id=brand_id).first()
        if not brand:
            return Response(
                {'error': 'Brand not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get date range (last 30 days)
        date_to = timezone.now()
        date_from = date_to - timedelta(days=30)

        # Gather all dashboard data
        dashboard_context = {
            'brand_name': brand.name,
            'kpis': get_brand_dashboard_kpis(brand_id, date_from, date_to),
            'heatmap': get_brand_heatmap_data(brand_id, date_from, date_to),
            'top_pain_points': get_brand_top_pain_points(brand_id, date_from, date_to),
            'community_watchlist': get_brand_community_watchlist(brand_id),
            'influencer_pulse': get_brand_influencer_pulse(brand_id),
            'campaign_analytics': get_brand_campaign_analytics(brand_id, date_from, date_to)
        }

        # Generate insights using LLM
        insights = _generate_insights_with_llm(dashboard_context)

        return Response({
            'insights': insights,
            'generated_at': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"AI insights generation error: {e}")
        return Response(
            {'error': f'Failed to generate insights: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _generate_insights_with_llm(dashboard_context):
    """Generate insights using LLM based on dashboard data."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
    import json

    # Initialize LLM
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.7)

    # Prepare context summary
    kpis = dashboard_context['kpis']
    pain_points = dashboard_context['top_pain_points']
    communities = dashboard_context['community_watchlist']
    campaign_analytics = dashboard_context['campaign_analytics']

    # Create prompt for LLM
    system_prompt = """You are an expert brand analytics consultant. Analyze the provided dashboard data and generate 4-6 concise, actionable insights.

Each insight should be:
- Specific and data-driven
- Actionable (what the brand should do)
- Clear and concise (1-2 sentences max)
- Focus on trends, opportunities, or risks

Format: Return ONLY a JSON array of insight strings, nothing else."""

    data_summary = f"""Brand: {dashboard_context['brand_name']}

KEY METRICS:
- Active Campaigns: {kpis.get('active_campaigns', 0)}
- High-Echo Communities: {kpis.get('high_echo_communities', 0)} (Change: {kpis.get('high_echo_change_percent', 0)}%)
- New Pain Points (>50% growth): {kpis.get('new_pain_points_above_50', 0)}
- Positivity Ratio: {kpis.get('positivity_ratio', 0)}% (Change: {kpis.get('positivity_change_pp', 0)} pp)

TOP PAIN POINTS:
{json.dumps([{'keyword': pp['keyword'], 'growth': pp['growth_percentage'], 'mentions': pp['mention_count']} for pp in pain_points[:5]], indent=2)}

COMMUNITY WATCHLIST:
{json.dumps([{'name': c['name'], 'platform': c['platform'], 'echo_score': c['echo_score'], 'echo_change': c['echo_change'], 'activity_score': c['activity_score']} for c in communities[:3]], indent=2)}

CAMPAIGN ANALYTICS:
- Total Campaigns: {campaign_analytics.get('total_campaigns', 0)}
- Active: {campaign_analytics.get('active_campaigns', 0)}
- Budget Utilization: {campaign_analytics.get('budget_utilization', 0)}%
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=data_summary)
        ]

        response = llm.invoke(messages)

        # Parse JSON response
        insights_text = response.content.strip()
        # Remove markdown code blocks if present
        if insights_text.startswith('```'):
            insights_text = insights_text.split('```')[1]
            if insights_text.startswith('json'):
                insights_text = insights_text[4:]
        insights_text = insights_text.strip()

        insights = json.loads(insights_text)

        # Ensure it's a list
        if not isinstance(insights, list):
            insights = [insights]

        return insights[:6]  # Limit to 6 insights

    except Exception as e:
        logger.error(f"LLM insight generation failed: {e}")
        # Return fallback insights
        return [
            f"Your brand has {kpis.get('high_echo_communities', 0)} high-echo communities with {kpis.get('high_echo_change_percent', 0):+.1f}% growth",
            f"Top pain point '{pain_points[0]['keyword'] if pain_points else 'N/A'}' is growing at {pain_points[0]['growth_percentage'] if pain_points else 0:+.0f}%",
            f"Community sentiment shows {kpis.get('positivity_ratio', 0):.0f}% positivity with {kpis.get('positivity_change_pp', 0):+.1f} pp change",
            f"Monitor {kpis.get('new_pain_points_above_50', 0)} rapidly growing pain points (>50% growth)",
            f"Campaign budget utilization at {campaign_analytics.get('budget_utilization', 0):.0f}% - {('optimize spending' if campaign_analytics.get('budget_utilization', 0) < 70 else 'on track')}"
        ]


# Update the create_brand function:
@api_view(['POST'])
@permission_classes([AllowAny])
def create_brand(request):
    """Create a new brand and automatically trigger scout analysis."""
    try:
        data = request.data
        brand_name = data.get('name', '').strip()
        
        if not brand_name:
            return Response(
                {'error': 'Brand name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the brand in database
        brand = Brand.objects.create(
            name=brand_name,
            description=data.get('description', ''),
            website=data.get('website', ''),
            industry=data.get('industry', '')
        )

        logger.info(f"✅ Brand created: {brand_name} (ID: {brand.id})")

        # Store keywords for later analysis
        keywords = data.get('keywords', [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        if not keywords:
            keywords = [brand_name, 'review', 'quality', 'problems']

        response_data = {
            'id': brand.id,
            'name': brand.name,
            'description': brand.description,
            'website': brand.website,
            'industry': brand.industry,
            'created_at': brand.created_at.isoformat(),
            'analysis_status': 'not_started',
            'keywords': keywords
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"❌ Brand creation failed: {e}")
        return Response(
            {'error': f'Brand creation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['POST'])
@permission_classes([AllowAny])
async def trigger_scout_analysis(request):
    """Trigger scout analysis directly for any brand."""
    try:
        data = request.data
        brand_name = data.get('brand_name', '').strip()
        keywords = data.get('keywords', [])
        brand_id = data.get('brand_id')
        scout_config = data.get('scout_config', {})  # Get enhanced config
        
        if not brand_name:
            return Response(
                {'error': 'Brand name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"🔍 Triggering scout analysis for: {brand_name} with config: {scout_config}")

        # Get brand if brand_id provided
        brand = None
        if brand_id:
            try:
                brand = Brand.objects.get(id=brand_id)
            except Brand.DoesNotExist:
                pass

        # Prepare keywords
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        
        if not keywords:
            keywords = [brand_name, 'review', 'quality', 'problems']

        # Execute scout analysis with enhanced config
        scout_results = await collect_real_brand_data(
            brand_name, 
            keywords,
            config=scout_config  # Pass the enhanced config
        )
        
        # Store results if we have a brand object
        if brand:
            await _store_brand_scout_data(brand, scout_results)

        response_data = {
            'brand_name': brand_name,
            'brand_id': brand.id if brand else None,
            'analysis_status': 'completed',
            'keywords_used': keywords,
            'scout_config_used': scout_config,
            'data_collected': {
                'communities': len(scout_results.get('communities', [])),
                'threads': len(scout_results.get('threads', [])),
                'pain_points': len(scout_results.get('pain_points', [])),
                'brand_mentions': len(scout_results.get('brand_mentions', []))
            },
            'summary': {
                'total_mentions_found': len(scout_results.get('brand_mentions', [])),
                'positive_sentiment_ratio': _calculate_positive_sentiment_ratio(scout_results),
                'top_pain_points': [pp.get('keyword') for pp in scout_results.get('pain_points', [])[:3]],
                'most_active_communities': [c.get('name') for c in scout_results.get('communities', [])[:3]],
                'analysis_focus': scout_config.get('focus', 'comprehensive'),
                'search_depth': scout_config.get('search_depth', 'comprehensive')
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"❌ Scout analysis failed: {e}")
        return Response(
            {'error': f'Scout analysis failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def control_brand_analysis(request, brand_id):
    """Start or stop brand analysis via Celery background tasks (NON-BLOCKING)."""
    try:
        action = request.data.get('action')  # 'start' or 'stop'

        if action not in ['start', 'stop']:
            return Response(
                {'error': 'Action must be "start" or "stop"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response(
                {'error': 'Brand not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if action == 'start':
            # Get the first user as owner
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner = User.objects.first()
            if not owner:
                owner = User.objects.create_user(username='system', email='system@echochamber.com')

            # Look for the AUTOMATIC campaign for this brand (not user-created campaigns)
            # Automatic campaigns are marked with metadata['is_auto_campaign'] = True
            # Only look for campaigns that are NOT completed
            campaign = Campaign.objects.filter(
                brand=brand,
                metadata__is_auto_campaign=True
            ).exclude(status='completed').first()

            if not campaign:
                # Get system settings for auto campaign interval
                from common.models import SystemSettings
                settings = SystemSettings.get_settings()
                from datetime import timedelta

                # Calculate first run times
                now = timezone.now()
                next_run = now + timedelta(seconds=settings.auto_campaign_interval)

                # Create a new automatic campaign for analysis
                # Automatic campaigns have NO end_date (run indefinitely until stopped)
                campaign = Campaign.objects.create(
                    name=f"{brand.name} - Brand Analytics",
                    brand=brand,
                    owner=owner,
                    status='active',
                    campaign_type='automatic',  # ✅ NEW: Set campaign type
                    schedule_enabled=True,
                    schedule_interval=settings.auto_campaign_interval,  # Use auto campaign interval from settings
                    description=f"Automatic brand analytics campaign for {brand.name}",
                    start_date=now,
                    end_date=None,  # No end date - runs until manually stopped
                    last_run_at=now,  # Mark as running now
                    next_run_at=next_run,  # Schedule next run
                    metadata={'is_auto_campaign': True}  # Mark as automatic
                )
                logger.info(f"📋 Created new automatic campaign for brand {brand.name}: {campaign.id} (interval: {settings.auto_campaign_interval}s)")
                logger.info(f"⏰ First run: NOW, Next run: {next_run}")
            else:
                # Reactivate the existing automatic campaign (if paused)
                from datetime import timedelta
                now = timezone.now()
                next_run = now + timedelta(seconds=campaign.schedule_interval)

                campaign.status = 'active'
                campaign.schedule_enabled = True
                if not campaign.start_date:
                    campaign.start_date = now
                campaign.last_run_at = now  # Mark as running now
                campaign.next_run_at = next_run  # Schedule next run
                campaign.save()
                logger.info(f"📋 Reactivated automatic campaign for brand {brand.name}: {campaign.id}")
                logger.info(f"⏰ First run: NOW, Next run: {next_run}")

            # ✅ FIX: Run immediately on start using Brand Analytics task
            from agents.tasks import scout_brand_analytics_task
            task_result = scout_brand_analytics_task.delay(brand_id=brand.id)

            logger.info(f"🚀 Running Brand Analytics immediately for brand {brand.name}: {task_result.id}")

            response_data = {
                'brand_id': brand.id,
                'brand_name': brand.name,
                'campaign_id': campaign.id,
                'analysis_status': 'running',
                'task_id': str(task_result.id),
                'schedule_interval': campaign.schedule_interval,
                'next_run_at': campaign.next_run_at.isoformat() if campaign.next_run_at else None,
                'message': f'Campaign started! Running first analysis now, then automatically every {campaign.schedule_interval}s. Use /api/v1/tasks/{{task_id}}/status/ to check progress.'
            }

            return Response(response_data, status=status.HTTP_202_ACCEPTED)  # 202 = Accepted (processing async)

        elif action == 'stop':
            # Stop (complete) ONLY the active automatic campaign for this brand
            # This marks it as completed so Start Analytics will create a new one
            updated_count = Campaign.objects.filter(
                brand=brand,
                metadata__is_auto_campaign=True,
                status__in=['active', 'paused']
            ).update(
                status='completed',
                schedule_enabled=False
            )

            logger.info(f"⏹️ Stopped automatic campaign for brand {brand.name} (marked {updated_count} campaign(s) as completed)")

            response_data = {
                'brand_id': brand.id,
                'brand_name': brand.name,
                'analysis_status': 'paused',
                'campaigns_paused': updated_count
            }

            return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"❌ Brand analysis control failed: {e}")
        return Response(
            {'error': f'Brand analysis control failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Add this helper function at the bottom of views.py:
def _calculate_positive_sentiment_ratio(scout_results):
    """Calculate ratio of positive sentiment in scout results."""
    threads = scout_results.get('threads', [])
    if not threads:
        return 0.0

    positive_count = sum(1 for thread in threads if thread.get('sentiment_score', 0) > 0)
    return round(positive_count / len(threads), 2)


def _get_brand_target_communities(brand):
    """
    Get target communities for a brand from multiple sources.

    Returns:
        List of subreddit/community names for targeting
    """
    from common.default_sources import get_reddit_subreddit_name

    communities = []

    # 1. Get from brand.sources field (can be source IDs or names)
    if brand.sources:
        logger.info(f"📋 Brand has {len(brand.sources)} configured sources")

        for source_ref in brand.sources:
            # Handle different formats
            if isinstance(source_ref, dict):
                # If it's a dict with id/name
                source_name = source_ref.get('name', source_ref.get('id', ''))
            else:
                # If it's a string (ID or name)
                source_name = str(source_ref)

            # Clean the name
            clean_name = get_reddit_subreddit_name(source_name)
            if clean_name:
                communities.append(clean_name)
                logger.info(f"  ✓ Added: {clean_name}")

    # Remove duplicates
    communities = list(set(communities))

    if communities:
        logger.info(f"📍 Found {len(communities)} target communities for {brand.name}: {communities}")
    else:
        logger.info(f"⚠️  No custom communities configured for {brand.name}, will use defaults")

    return communities

@api_view(['GET'])
@permission_classes([AllowAny])
def get_brands(request):
    """Get all brands with their latest scout analysis status."""
    try:
        brands = Brand.objects.all().order_by('-created_at')
        
        brands_data = []
        for brand in brands:
            # Get the AUTOMATIC campaign only (not user-created campaigns) for brand status
            auto_campaign = Campaign.objects.filter(
                brand=brand,
                metadata__is_auto_campaign=True
            ).first()

            brand_data = {
                'id': brand.id,
                'name': brand.name,
                'description': brand.description,
                'website': brand.website,
                'industry': brand.industry,
                'created_at': brand.created_at.isoformat(),
                'last_analysis': auto_campaign.created_at.isoformat() if auto_campaign else None,
                'analysis_status': auto_campaign.status if auto_campaign else 'never_analyzed',
                'communities_count': Community.objects.filter(brand=brand).count(),
                'pain_points_count': PainPoint.objects.filter(brand=brand).count(),
                'threads_count': Thread.objects.filter(brand=brand).count(),
                'campaign_count': Campaign.objects.filter(brand=brand).count()  # Total campaigns (including user-created)
            }
            brands_data.append(brand_data)
        
        return Response({
            'brands': brands_data,
            'total_count': len(brands_data)
        })

    except Exception as e:
        return Response(
            {'error': f'Failed to get brands: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def _store_brand_scout_data(brand, scout_results):
    """Store scout analysis results in database"""
    try:
        from django.utils import timezone
        from common.models import Campaign, Community, PainPoint, Thread
        
        logger.info(f"📊 Storing scout data for brand {brand.name}")
        
        # Create a campaign for this brand analysis
        campaign = Campaign.objects.create(
            name=f"Scout Analysis - {brand.name}",
            description=f"Automated scout analysis for brand {brand.name}",
            brand=brand,
            status='completed',
            budget_limit=50.0,
            current_spend=2.5,
            created_at=timezone.now()
        )
        
        # Store communities and track them for thread linking
        communities_map = {}  # name -> community object
        communities_created = []
        
        for community_data in scout_results.get('communities', []):
            try:
                community = Community.objects.create(
                    name=community_data['name'],
                    platform=community_data['platform'],
                    url=community_data.get('url', ''),
                    member_count=community_data.get('member_count', 0),
                    echo_score=community_data.get('echo_score', 0.0),
                    echo_score_change=community_data.get('echo_score_change', 0.0),
                    activity_level=community_data.get('activity_level', 'medium'),
                    is_active=True,
                    last_analyzed=timezone.now()
                )
                communities_created.append(community)
                communities_map[community.name] = community
                
            except Exception as e:
                logger.warning(f"Failed to create community {community_data.get('name')}: {e}")
                continue
        
        # Store pain points
        pain_points_created = []
        for pain_point_data in scout_results.get('pain_points', []):
            try:
                pain_point = PainPoint.objects.create(
                    keyword=pain_point_data['keyword'],
                    campaign=campaign,
                    mention_count=pain_point_data.get('mention_count', 0),
                    growth_percentage=pain_point_data.get('growth_percentage', 0.0),
                    sentiment_score=pain_point_data.get('sentiment_score', 0.0),
                    heat_level=pain_point_data.get('heat_level', 1),
                    severity=pain_point_data.get('severity', 'medium'),
                    category=pain_point_data.get('category', 'general'),
                    trend_direction=pain_point_data.get('trend_direction', 'stable'),
                    priority_score=pain_point_data.get('priority_score', 0.0),
                    created_at=timezone.now()
                )
                pain_points_created.append(pain_point)
                
            except Exception as e:
                logger.warning(f"Failed to create pain point {pain_point_data.get('keyword')}: {e}")
                continue
        
        # Store threads
        threads_created = []
        for thread_data in scout_results.get('threads', []):
            try:
                # Find the community for this thread
                community = None
                thread_community_name = thread_data.get('community', '')
                if thread_community_name and thread_community_name in communities_map:
                    community = communities_map[thread_community_name]
                
                # Handle content length
                content = thread_data.get('content', '')
                if len(content) > 2000:
                    content = content[:1997] + "..."
                
                # Parse created_at if it's a string
                created_at = thread_data.get('created_at')
                if isinstance(created_at, str):
                    try:
                        from datetime import datetime
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        created_at = timezone.now()
                elif not created_at:
                    created_at = timezone.now()
                
                thread = Thread.objects.create(
                    thread_id=thread_data['thread_id'],
                    title=thread_data.get('title', 'Untitled'),
                    content=content,
                    author=thread_data.get('author', 'unknown'),
                    url=thread_data.get('url', ''),
                    echo_score=thread_data.get('echo_score', 0.0),
                    sentiment_score=thread_data.get('sentiment_score', 0.0),
                    platform=thread_data.get('platform', 'unknown'),
                    community=community,
                    brand_mentioned=thread_data.get('brand_mentioned', False),
                    discussion_type=thread_data.get('discussion_type', 'general_discussion'),
                    created_at=created_at,
                    analyzed_at=timezone.now()
                )
                threads_created.append(thread)
                
            except Exception as e:
                logger.warning(f"Failed to create thread {thread_data.get('thread_id')}: {e}")
                continue
        
        # Link pain points to threads (many-to-many relationship)
        for thread in threads_created:
            try:
                thread_content_lower = thread.content.lower()
                for pain_point in pain_points_created:
                    # Check if pain point keyword appears in thread content
                    if pain_point.keyword.lower() in thread_content_lower:
                        thread.pain_points.add(pain_point)
            except Exception as e:
                logger.warning(f"Failed to link pain points to thread {thread.thread_id}: {e}")
        
        # Store scout metadata in campaign
        try:
            scout_metadata = {
                'config_used': scout_results.get('config_used', {}),
                'keywords_used': scout_results.get('keywords_used', []),
                'search_parameters': scout_results.get('search_parameters', {}),
                'data_sources': scout_results.get('data_sources', []),
                'collection_timestamp': scout_results.get('collection_timestamp'),
                'is_real_data': scout_results.get('is_real_data', True),
                'total_communities': len(communities_created),
                'total_pain_points': len(pain_points_created),
                'total_threads': len(threads_created)
            }
            
            # Store metadata (assuming your Campaign model has a metadata field)
            if hasattr(campaign, 'metadata'):
                campaign.metadata = scout_metadata
                campaign.save()
                
        except Exception as e:
            logger.warning(f"Failed to store scout metadata: {e}")
        
        logger.info(f"✅ Successfully stored scout data:")
        logger.info(f"   • Campaign ID: {campaign.id}")
        logger.info(f"   • {len(communities_created)} communities")
        logger.info(f"   • {len(pain_points_created)} pain points")
        logger.info(f"   • {len(threads_created)} threads")
        
        return {
            'success': True,
            'campaign_id': campaign.id,
            'communities_count': len(communities_created),
            'pain_points_count': len(pain_points_created),
            'threads_count': len(threads_created),
            'metadata': scout_metadata
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to store scout data: {e}")
        raise Exception(f"Database storage failed: {str(e)}")


@api_view(['GET'])
@permission_classes([AllowAny])
def get_scout_results(request, brand_id):
    """Get scout results for a specific brand."""
    try:
        brand = Brand.objects.get(id=brand_id)
        campaigns = Campaign.objects.filter(brand=brand).order_by('-created_at')
        
        if not campaigns.exists():
            return Response({'error': 'No scout analysis found for this brand'}, status=404)
        
        latest_campaign = campaigns.first()
        
        # Get related data
        communities = Community.objects.filter(thread__pain_points__campaign=latest_campaign).distinct()
        pain_points = PainPoint.objects.filter(campaign=latest_campaign)
        threads = Thread.objects.filter(pain_points__campaign=latest_campaign).distinct()
        
        return Response({
            'brand': {'id': brand.id, 'name': brand.name},
            'campaign': {'id': latest_campaign.id, 'created_at': latest_campaign.created_at},
            'summary': {
                'communities_found': communities.count(),
                'pain_points_identified': pain_points.count(),
                'threads_collected': threads.count(),
                'analysis_status': latest_campaign.status
            }
        })
        
    except Brand.DoesNotExist:
        return Response({'error': 'Brand not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_brand_influencers(request, brand_id):
    """Get top influencers for a brand."""
    try:
        brand = Brand.objects.get(id=brand_id)

        # Get optional query parameters
        limit = int(request.GET.get('limit', 20))
        min_score = float(request.GET.get('min_score', 0.0))
        campaign_id = request.GET.get('campaign')
        community_name = request.GET.get('community')  # NEW: Filter by community

        # Build query
        query = Influencer.objects.filter(brand=brand, influence_score__gte=min_score)

        if campaign_id:
            query = query.filter(campaign_id=campaign_id)

        # NEW: Filter by community name if provided
        if community_name:
            query = query.filter(community__name=community_name)

        # Get influencers sorted by influence score
        influencers = query.order_by('-influence_score')[:limit]

        # Serialize influencer data
        influencer_data = []
        for inf in influencers:
            influencer_data.append({
                'id': str(inf.id),
                'username': inf.username,
                'display_name': inf.display_name or inf.username,
                'platform': inf.platform,
                'profile_url': inf.profile_url,

                # Influence scores
                'reach_score': inf.reach_score,
                'authority_score': inf.authority_score,
                'advocacy_score': inf.advocacy_score,
                'relevance_score': inf.relevance_score,
                'influence_score': inf.influence_score,

                # Engagement metrics
                'total_posts': inf.total_posts,
                'total_karma': inf.total_karma,
                'avg_post_score': inf.avg_post_score,
                'total_comments': inf.total_comments,
                'avg_engagement_rate': inf.avg_engagement_rate,

                # Brand sentiment
                'sentiment': inf.sentiment_towards_brand,
                'brand_mention_count': inf.brand_mention_count,
                'brand_mention_rate': inf.brand_mention_rate,

                # Activity
                'communities': inf.communities,
                'post_frequency': inf.post_frequency,
                'last_active': inf.last_active.isoformat() if inf.last_active else None,

                # Community info
                'community': {
                    'id': str(inf.community.id),
                    'name': inf.community.name,
                    'platform': inf.community.platform
                } if inf.community else None
            })

        return Response({
            'brand': {
                'id': str(brand.id),
                'name': brand.name
            },
            'influencers': influencer_data,
            'total_count': len(influencer_data),
            'filters': {
                'limit': limit,
                'min_score': min_score,
                'campaign_id': campaign_id,
                'community': community_name  # NEW: Include community filter
            }
        })

    except Brand.DoesNotExist:
        return Response(
            {'error': 'Brand not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching influencers: {str(e)}")
        return Response(
            {'error': f'Failed to fetch influencers: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_brand_analysis_summary(request, brand_id):
    """
    Get comprehensive analysis summary with AI-powered insights for Brand Analytics.

    This generates insights based on Brand Analytics data (not campaign-specific data).
    """
    try:
        brand = Brand.objects.get(id=brand_id)

        # Get Brand Analytics data
        brand_kpis = get_brand_dashboard_kpis(brand_id, None, None)
        brand_communities = get_brand_community_watchlist(brand_id)
        brand_pain_points = get_brand_top_pain_points(brand_id, None, None)
        brand_influencers = get_brand_influencer_pulse(brand_id)

        # Check if we have any data
        has_data = (
            brand_kpis.get('active_campaigns', 0) > 0 or
            len(brand_communities) > 0 or
            len(brand_pain_points) > 0
        )

        if not has_data:
            return Response(
                {
                    'brand': {'id': str(brand.id), 'name': brand.name},
                    'message': 'No brand analytics data available yet. Please run brand analysis.',
                    'status': 'pending'
                }
            )

        # ✅ FIX: Get AI-powered insights from automatic campaign metadata (if already generated)
        automatic_campaign = Campaign.objects.filter(
            brand_id=brand_id,
            campaign_type='automatic'
        ).first()

        ai_insights = []
        if automatic_campaign and automatic_campaign.metadata.get('ai_insights'):
            # Use stored insights from automatic campaign
            ai_insights = automatic_campaign.metadata.get('ai_insights', [])
            logger.info(f"📊 Retrieved {len(ai_insights)} stored AI insights for Brand Analytics")
        else:
            # Generate new AI-powered insights based on Brand Analytics data
            from agents.analyst import generate_ai_powered_insights_from_brand_analytics

            try:
                ai_insights = generate_ai_powered_insights_from_brand_analytics(
                    brand=brand,
                    kpis=brand_kpis,
                    communities=brand_communities,
                    pain_points=brand_pain_points,
                    influencers=brand_influencers
                )

                # Store generated insights in automatic campaign
                if automatic_campaign:
                    if not automatic_campaign.metadata:
                        automatic_campaign.metadata = {}
                    automatic_campaign.metadata['ai_insights'] = ai_insights
                    automatic_campaign.save()
                    logger.info(f"💾 Stored {len(ai_insights)} new AI insights in automatic campaign")

            except Exception as insight_error:
                logger.error(f"Error generating AI insights: {insight_error}")
                # Fallback to empty insights if AI generation fails
                ai_insights = []

        # Prepare summary data
        summary_data = {
            'key_insights': ai_insights,
            'overview': {
                'total_campaigns': brand_kpis.get('active_campaigns', 0),
                'high_echo_communities': brand_kpis.get('high_echo_communities', 0),
                'pain_points_above_50': brand_kpis.get('new_pain_points_above_50', 0),
                'positivity_ratio': brand_kpis.get('positivity_ratio', 0),
            },
            'community_insights': {
                'total_communities': len(brand_communities),
                'top_communities': brand_communities[:5]
            },
            'pain_point_summary': {
                'total_pain_points': len(brand_pain_points),
                'top_pain_points': brand_pain_points[:5]
            },
            'influencer_summary': {
                'total_influencers': len(brand_influencers),
                'top_influencers': brand_influencers[:5]
            }
        }

        return Response({
            'brand': {
                'id': str(brand.id),
                'name': brand.name
            },
            'summary': summary_data,
            'status': 'completed'
        })

    except Brand.DoesNotExist:
        return Response(
            {'error': 'Brand not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching analysis summary: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to fetch analysis summary: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_communities(request):
    """Get communities, optionally filtered by brand."""
    brand_id = request.GET.get('brand')

    try:
        if brand_id:
            communities = Community.objects.filter(brand_id=brand_id).distinct()
        else:
            communities = Community.objects.all()
        
        communities_data = [
            {
                'id': c.id,
                'name': c.name,
                'platform': c.platform,
                'echo_score': c.echo_score,
                'member_count': c.member_count
            }
            for c in communities
        ]
        
        return Response({'communities': communities_data})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_pain_points(request):
    """Get pain points, optionally filtered by brand."""
    brand_id = request.GET.get('brand')
    
    try:
        if brand_id:
            pain_points = PainPoint.objects.filter(brand_id=brand_id)
        else:
            pain_points = PainPoint.objects.all()
        
        pain_points_data = [
            {
                'id': pp.id,
                'keyword': pp.keyword,
                'mention_count': pp.mention_count,
                'growth_percentage': pp.growth_percentage,
                'heat_level': pp.heat_level
            }
            for pp in pain_points
        ]
        
        return Response({'pain_points': pain_points_data})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_threads(request):
    """Get threads, optionally filtered by brand or community."""
    brand_id = request.GET.get('brand')
    community_param = request.GET.get('community')  # Can be ID or name

    try:
        threads = Thread.objects.all()

        if brand_id:
            threads = threads.filter(brand_id=brand_id)

        # NEW: Accept both community ID and community name
        if community_param:
            # Try to filter by name first (since frontend sends name)
            threads = threads.filter(community__name=community_param)

        threads = threads.distinct().order_by('-published_at')[:50]  # Limit to 50 most recent

        # NEW: Return full thread data for modal display
        threads_data = [
            {
                'id': str(t.id),
                'thread_id': t.thread_id,
                'title': t.title,
                'content': t.content,
                'author': t.author,
                'echo_score': float(t.echo_score),
                'sentiment_score': float(t.sentiment_score),
                'published_at': t.published_at.isoformat() if t.published_at else None,
                'comment_count': t.comment_count,
                'upvotes': t.upvotes,
                'community': {
                    'id': str(t.community.id),
                    'name': t.community.name,
                    'platform': t.community.platform
                } if t.community else None
            }
            for t in threads
        ]

        return Response({'threads': threads_data})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# DEPRECATED: Campaign creation is now handled directly in get_campaigns() POST
# This function is kept for reference but should not be called directly
# @api_view(['POST'])
# @permission_classes([AllowAny])
# def create_campaign(request):
#     """DEPRECATED - Use POST to /api/v1/campaigns/ instead"""
#     pass


async def _store_campaign_scout_data(campaign, scout_results):
    """Store scout analysis results for a campaign."""
    try:
        # Store communities
        communities_created = 0
        for community_data in scout_results.get('communities', []):
            community, created = Community.objects.get_or_create(
                name=community_data.get('name', 'Unknown'),
                platform=community_data.get('platform', 'reddit'),
                defaults={
                    'member_count': community_data.get('member_count', 0),
                    'echo_score': 0.0,
                    'campaign': campaign
                }
            )
            if created:
                communities_created += 1
        
        # Store threads
        threads_created = 0
        for thread_data in scout_results.get('threads', []):
            # Find or create community for thread
            community_name = thread_data.get('community', 'General')
            community, _ = Community.objects.get_or_create(
                name=community_name,
                platform=thread_data.get('platform', 'reddit'),
                defaults={
                    'member_count': 0,
                    'echo_score': 0.0,
                    'campaign': campaign
                }
            )
            
            thread, created = Thread.objects.get_or_create(
                thread_id=thread_data.get('id', f"campaign_{campaign.id}_{threads_created}"),
                defaults={
                    'title': thread_data.get('title', ''),
                    'content': thread_data.get('content', ''),
                    'platform': thread_data.get('platform', 'reddit'),
                    'echo_score': thread_data.get('engagement_metrics', {}).get('score', 0),
                    'sentiment_score': thread_data.get('sentiment_score', 0.0),
                    'community': community
                }
            )
            if created:
                threads_created += 1
        
        # Store pain points linked to campaign
        pain_points_created = 0
        for pain_point_data in scout_results.get('pain_points', []):
            pain_point, created = PainPoint.objects.get_or_create(
                keyword=pain_point_data.get('category', 'Unknown'),
                campaign=campaign,
                defaults={
                    'mention_count': pain_point_data.get('frequency', 1),
                    'growth_percentage': 0.0,
                    'heat_level': pain_point_data.get('severity_score', 5)
                }
            )
            if created:
                pain_points_created += 1
        
        logger.info(f"📊 Stored scout data for campaign {campaign.name}: "
                   f"{communities_created} communities, {threads_created} threads, "
                   f"{pain_points_created} pain points")
        
    except Exception as e:
        logger.error(f"❌ Failed to store scout data for campaign {campaign.name}: {e}")
        raise


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def get_campaigns(request):
    """Get campaigns (GET) or create new campaign (POST)."""

    # Handle POST - create campaign
    if request.method == 'POST':
        try:
            data = request.data

            # Validate required fields
            if not data.get('name'):
                return Response({'error': 'Campaign name is required'}, status=400)

            if not data.get('brand'):
                return Response({'error': 'Brand ID is required'}, status=400)

            # Check if brand exists
            try:
                brand = Brand.objects.get(id=data.get('brand'))
            except Brand.DoesNotExist:
                return Response({'error': 'Brand not found'}, status=404)

            logger.info(f"🚀 Creating campaign: {data.get('name')} for brand: {brand.name}")

            # Get the first user as owner (or create a default one)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner = User.objects.first()
            if not owner:
                # Create default system user if none exists
                owner = User.objects.create_user(username='system', email='system@echochamber.com')

            # Parse dates if provided
            from dateutil import parser as date_parser
            start_date = None
            end_date = None

            if data.get('start_date'):
                try:
                    start_date = date_parser.parse(data.get('start_date'))
                except:
                    pass

            if data.get('end_date'):
                try:
                    end_date = date_parser.parse(data.get('end_date'))
                except:
                    pass

            # Get system settings for schedule interval
            from common.models import SystemSettings
            settings = SystemSettings.get_settings()

            # Use custom campaign interval from settings
            schedule_interval = settings.custom_campaign_interval  # Default from settings

            # Create campaign (SYNCHRONOUS - NO SCOUT)
            # Use schedule_enabled from request, default to True for automatic scheduling
            campaign = Campaign.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
                brand=brand,
                owner=owner,
                status=data.get('status', 'active'),  # Default to active
                daily_budget=data.get('budget', 10.00),
                budget_limit=data.get('budget_limit'),  # Total budget limit
                start_date=start_date,
                end_date=end_date,
                schedule_enabled=data.get('schedule_enabled', True),  # Enable scheduling by default
                schedule_interval=schedule_interval  # Use settings interval
            )

            logger.info(f"✅ Campaign created: {campaign.id}")

            # Build response
            response_data = {
                'id': campaign.id,
                'name': campaign.name,
                'description': campaign.description,
                'brand': {
                    'id': brand.id,
                    'name': brand.name
                },
                'budget': float(campaign.daily_budget),
                'status': campaign.status,
                'created_at': campaign.created_at
            }

            # OPTIONAL: Schedule immediate scout if user requests it
            if data.get('run_scout_immediately', False):
                from agents.tasks import scout_reddit_task
                task_result = scout_reddit_task.delay(campaign_id=campaign.id)

                logger.info(f"📅 Scheduled immediate scout task: {task_result.id}")

                response_data['scout_analysis'] = {
                    'status': 'scheduled',
                    'task_id': str(task_result.id),
                    'message': 'Scout analysis scheduled. Use /api/v1/tasks/{task_id}/status/ to check progress.'
                }
            else:
                response_data['scout_analysis'] = {
                    'status': 'will_run_hourly',
                    'message': 'Campaign will be analyzed by scheduled hourly scout task'
                }

            return Response(response_data, status=201)

        except Exception as e:
            logger.error(f"❌ Campaign creation failed: {e}")
            return Response({'error': str(e)}, status=500)

    # Handle GET - list campaigns
    brand_id = request.GET.get('brand')

    try:
        if brand_id:
            campaigns = Campaign.objects.filter(brand_id=brand_id)
        else:
            campaigns = Campaign.objects.all()

        campaigns = campaigns.select_related('brand').order_by('-created_at')

        campaigns_data = [
            {
                'id': str(c.id),
                'name': c.name,
                'description': c.description,
                'brand': str(c.brand.id) if c.brand else None,
                'brand_name': c.brand.name if c.brand else None,
                'status': c.status,
                'keywords': c.keywords,
                'owner': c.owner.id,
                'schedule_enabled': c.schedule_enabled,
                'schedule_interval': c.schedule_interval,
                'budget_limit': float(c.budget_limit) if c.budget_limit else float(c.daily_budget),
                'current_spend': float(c.current_spend),
                'created_at': c.created_at.isoformat() if c.created_at else None,
                'last_run_at': c.last_run_at.isoformat() if c.last_run_at else None,
                'next_run_at': c.next_run_at.isoformat() if c.next_run_at else None,
                'start_date': c.start_date.isoformat() if c.start_date else None,
                'end_date': c.end_date.isoformat() if c.end_date else None,
                'is_auto_campaign': c.metadata.get('is_auto_campaign', False)  # Flag for automatic campaigns
            }
            for c in campaigns
        ]

        return Response({'campaigns': campaigns_data})

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def get_campaign_detail(request, campaign_id):
    """Get, update or delete a specific campaign."""
    try:
        campaign = Campaign.objects.select_related('brand').get(id=campaign_id)

        if request.method == 'PUT':
            # Check if this is an automatic campaign
            is_auto = campaign.metadata.get('is_auto_campaign', False)

            # Update campaign
            data = request.data

            # Track if status is changing from paused/inactive to active
            old_status = campaign.status
            new_status = data.get('status')
            should_run_immediately = False

            # Update basic fields (but protect auto campaign name)
            if 'name' in data and not is_auto:
                campaign.name = data['name']
            if 'description' in data:
                campaign.description = data['description']
            if 'budget' in data:
                campaign.daily_budget = data['budget']
            if 'status' in data:
                campaign.status = data['status']

                # If reactivating a paused campaign, set it to run immediately
                if old_status in ['paused', 'inactive'] and new_status == 'active':
                    should_run_immediately = True
                    now = timezone.now()
                    next_run = now + timedelta(seconds=campaign.schedule_interval)

                    campaign.schedule_enabled = True
                    campaign.last_run_at = now
                    campaign.next_run_at = next_run
                    logger.info(f"📋 Reactivating campaign {campaign.name}: will run immediately")
                    logger.info(f"⏰ First run: NOW, Next run: {next_run}")

            campaign.save()

            # ✅ FIX: Run immediately if reactivating, using appropriate task based on campaign type
            if should_run_immediately:
                if campaign.campaign_type == 'automatic':
                    from agents.tasks import scout_brand_analytics_task
                    task_result = scout_brand_analytics_task.delay(brand_id=campaign.brand_id)
                    logger.info(f"🚀 Running Brand Analytics immediately: {task_result.id}")
                else:
                    from agents.tasks import scout_custom_campaign_task
                    task_result = scout_custom_campaign_task.delay(campaign_id=campaign.id)
                    logger.info(f"🚀 Running Custom Campaign immediately: {task_result.id}")

            return Response({
                'id': str(campaign.id),
                'name': campaign.name,
                'description': campaign.description,
                'brand': {
                    'id': str(campaign.brand.id) if campaign.brand else None,
                    'name': campaign.brand.name if campaign.brand else None
                },
                'daily_budget': float(campaign.daily_budget),
                'status': campaign.status,
                'created_at': campaign.created_at.isoformat() if campaign.created_at else None
            })

        elif request.method == 'DELETE':
            # Check if this is an automatic campaign - prevent deletion
            is_auto = campaign.metadata.get('is_auto_campaign', False)
            if is_auto:
                return Response(
                    {'error': 'Cannot delete automatic brand analytics campaign. Use brand Start/Pause controls instead.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Hard delete - actually remove from database
            campaign_name = campaign.name
            campaign.delete()
            logger.info(f"🗑️ Deleted campaign: {campaign_name}")
            return Response(status=status.HTTP_204_NO_CONTENT)

        # GET - Get detailed information
        # Get related data
        pain_points = PainPoint.objects.filter(campaign=campaign)
        communities = Community.objects.filter(campaign=campaign)

        campaign_data = {
            'id': str(campaign.id),
            'name': campaign.name,
            'description': campaign.description,
            'brand': {
                'id': str(campaign.brand.id) if campaign.brand else None,
                'name': campaign.brand.name if campaign.brand else None
            },
            'daily_budget': float(campaign.daily_budget),
            'current_spend': float(campaign.current_spend),
            'status': campaign.status,
            'schedule_enabled': campaign.schedule_enabled,
            'last_run_at': campaign.last_run_at.isoformat() if campaign.last_run_at else None,
            'next_run_at': campaign.next_run_at.isoformat() if campaign.next_run_at else None,
            'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
            'pain_points_count': pain_points.count(),
            'communities_count': communities.count(),
            'pain_points': [
                {
                    'id': str(pp.id),
                    'keyword': pp.keyword,
                    'mention_count': pp.mention_count,
                    'heat_level': pp.heat_level
                }
                for pp in pain_points[:10]  # Top 10 pain points
            ],
            'communities': [
                {
                    'id': str(c.id),
                    'name': c.name,
                    'platform': c.platform,
                    'member_count': c.member_count
                }
                for c in communities[:10]  # Top 10 communities
            ]
        }

        return Response(campaign_data)

    except Campaign.DoesNotExist:
        return Response({'error': 'Campaign not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# Task Management and Monitoring Endpoints

@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_scout_task(request):
    """
    Manually trigger a scout data collection task.

    POST /api/v1/tasks/scout/
    Body: {
        "campaign_id": <optional int>,
        "config": <optional dict>
    }
    """
    try:
        from agents.tasks import scout_reddit_task

        campaign_id = request.data.get('campaign_id')
        config = request.data.get('config', {})

        # Trigger task asynchronously
        task = scout_reddit_task.delay(campaign_id=campaign_id, config=config)

        return Response({
            'task_id': task.id,
            'status': 'pending',
            'message': 'Scout task triggered successfully',
            'campaign_id': campaign_id
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Failed to trigger scout task: {e}")
        return Response(
            {'error': f'Failed to trigger task: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_insights_task(request):
    """
    Manually trigger daily insights generation task.

    POST /api/v1/tasks/insights/
    Body: {
        "campaign_id": <optional int>
    }
    """
    try:
        from agents.tasks import generate_daily_insights_task

        campaign_id = request.data.get('campaign_id')

        # Trigger task asynchronously
        task = generate_daily_insights_task.delay(campaign_id=campaign_id)

        return Response({
            'task_id': task.id,
            'status': 'pending',
            'message': 'Insights generation task triggered successfully',
            'campaign_id': campaign_id
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Failed to trigger insights task: {e}")
        return Response(
            {'error': f'Failed to trigger task: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_cleanup_task(request):
    """
    Manually trigger data cleanup task.

    POST /api/v1/tasks/cleanup/
    Body: {
        "days_to_keep": <optional int, default 90>
    }
    """
    try:
        from agents.tasks import cleanup_old_data_task

        days_to_keep = request.data.get('days_to_keep', 90)

        # Trigger task asynchronously
        task = cleanup_old_data_task.delay(days_to_keep=days_to_keep)

        return Response({
            'task_id': task.id,
            'status': 'pending',
            'message': 'Cleanup task triggered successfully',
            'days_to_keep': days_to_keep
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Failed to trigger cleanup task: {e}")
        return Response(
            {'error': f'Failed to trigger task: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_workflow_task(request):
    """
    Manually trigger a complete campaign analysis workflow.

    POST /api/v1/tasks/workflow/
    Body: {
        "campaign_id": <required int>,
        "workflow_type": <optional str, default "content_analysis">
    }
    """
    try:
        from agents.tasks import run_campaign_analysis_workflow

        campaign_id = request.data.get('campaign_id')
        workflow_type = request.data.get('workflow_type', 'content_analysis')

        if not campaign_id:
            return Response(
                {'error': 'campaign_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Trigger task asynchronously
        task = run_campaign_analysis_workflow.delay(
            campaign_id=campaign_id,
            workflow_type=workflow_type
        )

        return Response({
            'task_id': task.id,
            'status': 'pending',
            'message': 'Workflow task triggered successfully',
            'campaign_id': campaign_id,
            'workflow_type': workflow_type
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Failed to trigger workflow task: {e}")
        return Response(
            {'error': f'Failed to trigger task: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def task_status(request, task_id):
    """
    Get the status of a Celery task.

    GET /api/v1/tasks/{task_id}/status/
    """
    try:
        from celery.result import AsyncResult

        task = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'status': task.state,
            'info': None
        }

        if task.state == 'PENDING':
            response_data['message'] = 'Task is waiting to be executed'
        elif task.state == 'STARTED':
            response_data['message'] = 'Task has started processing'
        elif task.state == 'SUCCESS':
            response_data['message'] = 'Task completed successfully'
            response_data['result'] = task.result
        elif task.state == 'FAILURE':
            response_data['message'] = 'Task failed'
            response_data['error'] = str(task.info)
        elif task.state == 'RETRY':
            response_data['message'] = 'Task is being retried'
            response_data['info'] = str(task.info)

        return Response(response_data)

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return Response(
            {'error': f'Failed to get task status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def monitoring_dashboard(request):
    """
    Get comprehensive monitoring dashboard data including:
    - Active workflows
    - Task statistics
    - Performance metrics
    - Error rates
    - Cost tracking

    GET /api/v1/monitoring/dashboard/
    """
    try:
        from django.core.cache import cache
        from celery import current_app
        from agents.monitoring import global_monitor

        # Get active tasks from Celery
        inspect = current_app.control.inspect()
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        reserved_tasks = inspect.reserved() or {}

        # Count total active tasks across all workers
        total_active = sum(len(tasks) for tasks in active_tasks.values())
        total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
        total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())

        # Get recent campaign metrics
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_insights = Insight.objects.filter(
            created_at__gte=recent_cutoff
        ).count()

        recent_content = ProcessedContent.objects.filter(
            created_at__gte=recent_cutoff
        ).count()

        # Get monitoring events from global monitor
        compliance_events = global_monitor.compliance_tracker.audit_events[-100:] if global_monitor.compliance_tracker.audit_events else []

        # Calculate error rate from recent events
        error_events = [e for e in compliance_events if e.get('event_type') in ['workflow_error', 'node_error']]
        error_rate = (len(error_events) / max(len(compliance_events), 1)) * 100

        # Get campaign statistics
        active_campaigns = Campaign.objects.filter(is_active=True).count()
        total_campaigns = Campaign.objects.count()

        # Get workflow statistics from database
        workflow_stats = {
            'total_insights_24h': recent_insights,
            'total_content_24h': recent_content,
            'active_campaigns': active_campaigns,
            'total_campaigns': total_campaigns
        }

        dashboard_data = {
            'timestamp': timezone.now().isoformat(),
            'celery_tasks': {
                'active': total_active,
                'scheduled': total_scheduled,
                'reserved': total_reserved,
                'workers': list(active_tasks.keys()) if active_tasks else []
            },
            'workflow_stats': workflow_stats,
            'monitoring': {
                'total_events': len(compliance_events),
                'error_rate': round(error_rate, 2),
                'recent_errors': error_events[-10:],
                'langsmith_enabled': global_monitor.client is not None
            },
            'system_health': {
                'database': 'connected',
                'celery': 'healthy' if total_active >= 0 else 'unknown',
                'monitoring': 'active'
            }
        }

        return Response(dashboard_data)

    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {e}")
        return Response(
            {'error': f'Failed to get dashboard data: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def workflow_metrics(request):
    """
    Get detailed workflow performance metrics.

    GET /api/v1/monitoring/workflows/metrics/
    Query params:
        - campaign_id: Filter by campaign
        - days: Number of days to look back (default 7)
    """
    try:
        campaign_id = request.GET.get('campaign_id')
        days = int(request.GET.get('days', 7))

        cutoff_date = timezone.now() - timedelta(days=days)

        # Base queryset
        campaigns_query = Campaign.objects.all()
        if campaign_id:
            campaigns_query = campaigns_query.filter(id=campaign_id)

        metrics_data = []

        for campaign in campaigns_query:
            # Get metrics for this campaign
            insights_count = Insight.objects.filter(
                campaign=campaign,
                created_at__gte=cutoff_date
            ).count()

            content_count = ProcessedContent.objects.filter(
                raw_content__campaign=campaign,
                created_at__gte=cutoff_date
            ).count()

            avg_sentiment = ProcessedContent.objects.filter(
                raw_content__campaign=campaign,
                created_at__gte=cutoff_date
            ).aggregate(avg_sentiment=Avg('sentiment_score'))['avg_sentiment'] or 0

            pain_points_count = PainPoint.objects.filter(
                campaign=campaign
            ).count()

            campaign_metrics = {
                'campaign_id': campaign.id,
                'campaign_name': campaign.name,
                'period_days': days,
                'insights_generated': insights_count,
                'content_processed': content_count,
                'average_sentiment': round(avg_sentiment, 3),
                'pain_points_tracked': pain_points_count,
                'last_scout_run': campaign.last_scout_run.isoformat() if hasattr(campaign, 'last_scout_run') and campaign.last_scout_run else None
            }

            metrics_data.append(campaign_metrics)

        return Response({
            'period_days': days,
            'campaigns_count': len(metrics_data),
            'metrics': metrics_data,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        return Response(
            {'error': f'Failed to get metrics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def agent_health(request):
    """
    Get health status of all workflow agents/nodes.

    GET /api/v1/monitoring/agents/health/
    """
    try:
        from agents.orchestrator import workflow_orchestrator

        agent_nodes = [
            'scout_node',
            'cleaner_node',
            'analyst_node',
            'chatbot_node',
            'monitoring_agent',
            'workflow_orchestrator'
        ]

        health_status = {}

        for agent_name in agent_nodes:
            # Check if agent/node is operational
            is_healthy = workflow_orchestrator.get_node_health(agent_name)

            health_status[agent_name] = {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'available': is_healthy,
                'last_check': timezone.now().isoformat()
            }

        overall_health = all(node['status'] == 'healthy' for node in health_status.values())

        return Response({
            'overall_status': 'healthy' if overall_health else 'degraded',
            'agents': health_status,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to get agent health: {e}")
        return Response(
            {'error': f'Failed to get health status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def restart_agent(request, agent_name):
    """
    Restart a specific agent/node.

    POST /api/v1/monitoring/agents/{agent_name}/restart/
    """
    try:
        from agents.orchestrator import workflow_orchestrator

        success = workflow_orchestrator.restart_node(agent_name)

        if success:
            return Response({
                'message': f'Agent {agent_name} restarted successfully',
                'agent_name': agent_name,
                'status': 'restarted',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return Response({
                'error': f'Failed to restart agent {agent_name}',
                'agent_name': agent_name
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Failed to restart agent: {e}")
        return Response(
            {'error': f'Failed to restart agent: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Source Management Endpoints

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_sources(request):
    """
    Get all sources (both default and custom).

    GET /api/v1/sources/
    Query params:
        - include_defaults: true/false (default: true)
        - platform: reddit|forum|discord|website
        - category: fashion|technology|reviews|etc
    """
    try:
        from common.models import Source
        from common.default_sources import get_all_default_sources

        include_defaults = request.GET.get('include_defaults', 'true').lower() == 'true'
        platform = request.GET.get('platform')
        category = request.GET.get('category')

        all_sources = []

        # Get default sources
        if include_defaults:
            default_sources = get_all_default_sources()

            # Filter by platform/category if requested
            if platform:
                default_sources = [s for s in default_sources if s['platform'] == platform]
            if category:
                default_sources = [s for s in default_sources if s.get('category') == category]

            all_sources.extend(default_sources)

        # Get custom sources from database
        custom_query = Source.objects.filter(is_active=True)

        if platform:
            custom_query = custom_query.filter(source_type=platform)
        if category:
            custom_query = custom_query.filter(category=category)

        custom_sources = [
            {
                'id': str(source.id),
                'name': source.name,
                'platform': source.source_type,
                'url': source.url,
                'description': source.description,
                'category': source.category,
                'is_default': False,
                'is_active': source.is_active,
                'created_at': source.created_at.isoformat()
            }
            for source in custom_query
        ]

        all_sources.extend(custom_sources)

        return Response({
            'sources': all_sources,
            'total': len(all_sources),
            'default_count': len([s for s in all_sources if s.get('is_default')]),
            'custom_count': len([s for s in all_sources if not s.get('is_default')])
        })

    except Exception as e:
        logger.error(f"Failed to get sources: {e}")
        return Response(
            {'error': f'Failed to get sources: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_custom_source(request):
    """
    Create a new custom source.

    POST /api/v1/sources/custom/
    Body: {
        "name": "r/CustomSubreddit",
        "platform": "reddit",
        "url": "https://reddit.com/r/CustomSubreddit",
        "description": "Custom subreddit description",
        "category": "fashion"
    }
    """
    try:
        from common.models import Source

        name = request.data.get('name')
        platform = request.data.get('platform')
        url = request.data.get('url')
        description = request.data.get('description', '')
        category = request.data.get('category', '')

        if not all([name, platform, url]):
            return Response(
                {'error': 'name, platform, and url are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if source already exists
        if Source.objects.filter(source_type=platform, url=url).exists():
            return Response(
                {'error': 'Source with this platform and URL already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create source
        source = Source.objects.create(
            name=name,
            source_type=platform,
            url=url,
            description=description,
            category=category,
            is_default=False,
            is_active=True
        )

        return Response({
            'id': str(source.id),
            'name': source.name,
            'platform': source.source_type,
            'url': source.url,
            'description': source.description,
            'category': source.category,
            'is_default': False,
            'message': 'Custom source created successfully'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Failed to create custom source: {e}")
        return Response(
            {'error': f'Failed to create custom source: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_custom_source(request, source_id):
    """
    Delete a custom source.

    DELETE /api/v1/sources/custom/{source_id}/
    """
    try:
        from common.models import Source

        source = Source.objects.get(id=source_id, is_default=False)
        source_name = source.name
        source.delete()

        return Response({
            'message': f'Source {source_name} deleted successfully'
        })

    except Source.DoesNotExist:
        return Response(
            {'error': 'Custom source not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Failed to delete custom source: {e}")
        return Response(
            {'error': f'Failed to delete custom source: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def system_settings(request):
    """
    Get or update system settings.
    
    GET /api/v1/settings/
    PUT /api/v1/settings/
    Body: {
        "custom_campaign_interval": 3600,
        "auto_campaign_interval": 3600
    }
    """
    from common.models import SystemSettings
    
    try:
        settings = SystemSettings.get_settings()
        
        if request.method == 'GET':
            return Response({
                'custom_campaign_interval': settings.custom_campaign_interval,
                'auto_campaign_interval': settings.auto_campaign_interval,
                'updated_at': settings.updated_at
            })
        
        elif request.method == 'PUT':
            # Update settings
            if 'custom_campaign_interval' in request.data:
                interval = int(request.data['custom_campaign_interval'])
                if interval < 60:  # Minimum 1 minute
                    return Response(
                        {'error': 'Custom campaign interval must be at least 60 seconds (1 minute)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                settings.custom_campaign_interval = interval

            if 'auto_campaign_interval' in request.data:
                interval = int(request.data['auto_campaign_interval'])
                if interval < 60:  # Minimum 1 minute
                    return Response(
                        {'error': 'Auto campaign interval must be at least 60 seconds (1 minute)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                settings.auto_campaign_interval = interval
            
            settings.save()
            
            logger.info(f"System settings updated: custom={settings.custom_campaign_interval}s, auto={settings.auto_campaign_interval}s")
            
            return Response({
                'custom_campaign_interval': settings.custom_campaign_interval,
                'auto_campaign_interval': settings.auto_campaign_interval,
                'updated_at': settings.updated_at,
                'message': 'Settings updated successfully'
            })
    
    except Exception as e:
        logger.error(f"Failed to handle system settings: {e}")
        return Response(
            {'error': f'Failed to handle system settings: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_discovered_sources(request):
    """
    Get all LLM-discovered sources from the database.

    This endpoint retrieves all source discoveries made by the LLM
    during campaign executions and stored in the database.

    Returns:
        List of discovered sources grouped by brand with:
        - brand_name: Brand analyzed
        - industry: Industry context
        - focus: Analysis focus
        - reddit_communities: List of Reddit subreddits
        - forums: List of forum domains
        - reasoning: LLM explanation
        - discovered_at: Discovery timestamp
        - cache_hit: Whether from cache
    """
    try:
        # Get all LLM-discovered sources from database
        llm_sources = Source.objects.filter(
            category='llm_discovered',
            is_active=True
        ).order_by('-created_at')

        logger.info(f"Found {llm_sources.count()} LLM-discovered sources in database")

        # Group sources by brand
        sources_by_brand = {}

        for source in llm_sources:
            brand_name = source.config.get('brand', 'Unknown')
            focus = source.config.get('focus', 'comprehensive')

            # Create unique key for this brand+focus combination
            key = f"{brand_name}_{focus}"

            if key not in sources_by_brand:
                sources_by_brand[key] = {
                    'brand_name': brand_name,
                    'focus': focus,
                    'industry': source.config.get('industry', 'general'),
                    'reddit_communities': [],
                    'forums': [],
                    'reasoning': source.config.get('reasoning', ''),
                    'discovered_at': source.config.get('discovered_at', source.created_at.isoformat()),
                    'cache_hit': source.config.get('cache_hit', False),
                    'is_fallback': source.config.get('is_fallback', False)
                }

            # Add to appropriate list based on source type
            if source.source_type == 'reddit':
                community_name = source.name.replace('r/', '')
                if community_name not in sources_by_brand[key]['reddit_communities']:
                    sources_by_brand[key]['reddit_communities'].append(community_name)
            elif source.source_type == 'forum':
                forum_domain = source.name
                if forum_domain not in sources_by_brand[key]['forums']:
                    sources_by_brand[key]['forums'].append(forum_domain)

        discovered_sources = list(sources_by_brand.values())

        logger.info(f"Retrieved {len(discovered_sources)} unique brand discoveries from database")

        return Response({
            'sources': discovered_sources,
            'count': len(discovered_sources),
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to get discovered sources: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'error': f'Failed to get discovered sources: {str(e)}', 'sources': []},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def discover_sources_api(request):
    """
    Trigger LLM source discovery for a specific brand.

    Query params:
        - brand: Brand name (required)
        - refresh: Force refresh cache (optional, default: false)
        - industry: Industry context (optional, default: 'general')
        - focus: Analysis focus (optional, default: 'comprehensive')

    Returns:
        Discovered sources for the brand
    """
    try:
        from agents.scout_data_collection import discover_sources_with_llm

        brand_name = request.GET.get('brand')
        if not brand_name:
            return Response(
                {'error': 'Brand name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = request.GET.get('refresh', 'false').lower() == 'true'
        industry = request.GET.get('industry', 'general')
        focus = request.GET.get('focus', 'comprehensive')

        logger.info(f"Discovering sources for brand: {brand_name}, refresh: {refresh}")

        # If refresh is requested, clear the cache first
        if refresh:
            from django.core.cache import cache
            cache_key = f"llm_sources_{brand_name}_{focus}_{industry}".lower().replace(" ", "_")
            cache.delete(cache_key)
            logger.info(f"Cleared cache for key: {cache_key}")

        # Run async discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        sources = loop.run_until_complete(
            discover_sources_with_llm(
                brand_name=brand_name,
                focus=focus,
                industry=industry,
                use_cache=not refresh
            )
        )

        loop.close()

        logger.info(f"Discovered {len(sources.get('reddit_communities', []))} Reddit communities and {len(sources.get('forums', []))} forums for {brand_name}")

        return Response(sources)

    except Exception as e:
        logger.error(f"Failed to discover sources: {e}")
        return Response(
            {'error': f'Failed to discover sources: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

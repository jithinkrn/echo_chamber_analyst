"""
API views for EchoChamber Analyst - LangGraph Integration.

This module provides API endpoints that use LangGraph workflows
instead of the custom agent system, providing better orchestration,
monitoring, and compliance tracking.
"""

import asyncio
import uuid
import logging
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from common.models import Campaign
from agents.orchestrator import workflow_orchestrator
from agents.state import CampaignContext, create_chat_state
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
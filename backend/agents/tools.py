"""
LangGraph Tools and API Integration

This module provides tools for LangGraph nodes to interact with databases,
APIs, and external services in a standardized way.
"""

from typing import Dict, List, Any, Optional, Union
import json
import asyncio
from datetime import datetime, timedelta
from functools import wraps

from langchain_core.tools import BaseTool
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities import SQLDatabase
from pydantic import BaseModel, Field

from django.db import connection
from django.conf import settings
from common.models import (
    Campaign, Source, RawContent, ProcessedContent,
    Insight, Influencer, AuditLog
)

# Import new RAG tools
from agents.hybrid_rag_tool import hybrid_rag_tool
from agents.vector_tools import vector_search_tool, hybrid_search_tool
from agents.dashboard_tools import (
    brand_analytics_tool,
    community_query_tool,
    influencer_query_tool,
    pain_point_analysis_tool,
    campaign_analytics_tool,
    trend_analysis_tool
)


class DatabaseQueryInput(BaseModel):
    """Input schema for database queries."""
    query: str = Field(description="SQL query to execute")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")


class ContentSearchInput(BaseModel):
    """Input schema for content search."""
    query: str = Field(description="Search query")
    campaign_id: Optional[str] = Field(default=None, description="Campaign ID to filter by")
    content_type: Optional[str] = Field(default=None, description="Content type filter")
    limit: int = Field(default=20, description="Maximum number of results")


class InsightCreationInput(BaseModel):
    """Input schema for creating insights."""
    insight_type: str = Field(description="Type of insight")
    title: str = Field(description="Insight title")
    description: str = Field(description="Insight description")
    confidence_score: float = Field(description="Confidence score (0-1)")
    priority_score: float = Field(description="Priority score (0-1)")
    tags: List[str] = Field(default=[], description="Tags for the insight")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class AuditLogInput(BaseModel):
    """Input schema for audit logging."""
    action_type: str = Field(description="Type of action")
    action_description: str = Field(description="Description of the action")
    agent_name: str = Field(description="Name of the agent performing the action")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


def with_error_handling(func):
    """Decorator to add error handling to tool functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    return wrapper


class DatabaseQueryTool(BaseTool):
    """Tool for executing SQL queries against the Django database."""

    name: str = "database_query"
    description: str = """
    Execute SQL queries against the EchoChamber Analyst database.
    Use this to retrieve campaign data, content, insights, and metrics.
    Always use parameterized queries to prevent SQL injection.
    """
    args_schema: type[BaseModel] = DatabaseQueryInput

    @with_error_handling
    async def _arun(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a database query asynchronously."""
        try:
            with connection.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if query.strip().upper().startswith('SELECT'):
                    columns = [col[0] for col in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    return {
                        "success": True,
                        "results": results,
                        "count": len(results)
                    }
                else:
                    return {
                        "success": True,
                        "rows_affected": cursor.rowcount
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous version of the database query."""
        return asyncio.run(self._arun(query, params))


class ContentSearchTool(BaseTool):
    """Tool for searching processed content and insights."""

    name: str = "content_search"
    description: str = """
    Search through processed content, insights, and campaign data.
    Use this to find relevant information for analysis or chat responses.
    """
    args_schema: type[BaseModel] = ContentSearchInput

    @with_error_handling
    async def _arun(
        self,
        query: str,
        campaign_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search content asynchronously."""
        results = []

        # Search in processed content
        content_queryset = ProcessedContent.objects.all()
        if campaign_id:
            content_queryset = content_queryset.filter(
                raw_content__campaign_id=campaign_id
            )

        # Simple text search (can be enhanced with full-text search)
        content_results = content_queryset.filter(
            cleaned_content__icontains=query
        )[:limit]

        for content in content_results:
            results.append({
                "type": "content",
                "id": str(content.id),
                "title": content.raw_content.title or "Untitled",
                "content": content.cleaned_content[:500] + "..." if len(content.cleaned_content) > 500 else content.cleaned_content,
                "sentiment_score": float(content.sentiment_score) if content.sentiment_score else None,
                "created_at": content.created_at.isoformat(),
                "source": content.raw_content.source.name if content.raw_content.source else None
            })

        # Search in insights
        insight_results = Insight.objects.filter(
            description__icontains=query
        )[:limit]

        for insight in insight_results:
            results.append({
                "type": "insight",
                "id": str(insight.id),
                "title": insight.title,
                "description": insight.description,
                "insight_type": insight.insight_type,
                "confidence_score": float(insight.confidence_score),
                "created_at": insight.created_at.isoformat(),
                "campaign": insight.campaign.name if insight.campaign else None
            })

        return {
            "success": True,
            "results": results,
            "total_found": len(results),
            "query": query
        }

    def _run(
        self,
        query: str,
        campaign_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Synchronous version of content search."""
        return asyncio.run(self._arun(query, campaign_id, content_type, limit))


class InsightCreationTool(BaseTool):
    """Tool for creating new insights in the database."""

    name: str = "create_insight"
    description: str = """
    Create a new insight based on analysis results.
    Use this when the analyst agent generates new insights from content analysis.
    """
    args_schema: type[BaseModel] = InsightCreationInput

    @with_error_handling
    async def _arun(
        self,
        insight_type: str,
        title: str,
        description: str,
        confidence_score: float,
        priority_score: float,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create an insight asynchronously."""
        try:
            insight = Insight.objects.create(
                insight_type=insight_type,
                title=title,
                description=description,
                confidence_score=confidence_score,
                priority_score=priority_score,
                tags=tags or [],
                metadata=metadata or {}
            )

            return {
                "success": True,
                "insight_id": str(insight.id),
                "title": insight.title,
                "created_at": insight.created_at.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run(
        self,
        insight_type: str,
        title: str,
        description: str,
        confidence_score: float,
        priority_score: float,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Synchronous version of insight creation."""
        return asyncio.run(self._arun(
            insight_type, title, description, confidence_score,
            priority_score, tags, metadata
        ))


class AuditLogTool(BaseTool):
    """Tool for creating audit log entries."""

    name: str = "create_audit_log"
    description: str = """
    Create an audit log entry for compliance and monitoring.
    Use this to track important actions and decisions in the workflow.
    """
    args_schema: type[BaseModel] = AuditLogInput

    @with_error_handling
    async def _arun(
        self,
        action_type: str,
        action_description: str,
        agent_name: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create an audit log entry asynchronously."""
        try:
            audit_log = AuditLog.objects.create(
                action_type=action_type,
                action_description=action_description,
                agent_name=agent_name,
                metadata=metadata or {}
            )

            return {
                "success": True,
                "log_id": str(audit_log.id),
                "timestamp": audit_log.created_at.isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run(
        self,
        action_type: str,
        action_description: str,
        agent_name: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Synchronous version of audit log creation."""
        return asyncio.run(self._arun(action_type, action_description, agent_name, metadata))


class CampaignStatsTool(BaseTool):
    """Tool for retrieving campaign statistics."""

    name: str = "get_campaign_stats"
    description: str = """
    Get comprehensive statistics for a specific campaign.
    Returns content counts, insights, metrics, and performance data.
    """

    @with_error_handling
    async def _arun(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign statistics asynchronously."""
        try:
            campaign = Campaign.objects.get(id=campaign_id)

            # Content statistics
            raw_content_count = RawContent.objects.filter(campaign=campaign).count()
            processed_content_count = ProcessedContent.objects.filter(
                raw_content__campaign=campaign
            ).count()

            # Insight statistics
            insights_count = Insight.objects.filter(campaign=campaign).count()
            validated_insights_count = Insight.objects.filter(
                campaign=campaign, is_validated=True
            ).count()

            # Influencer statistics
            influencers_count = Influencer.objects.filter(campaign=campaign).count()

            # Performance metrics
            recent_activity = AuditLog.objects.filter(
                campaign=campaign,
                created_at__gte=datetime.now() - timedelta(days=7)
            ).count()

            return {
                "success": True,
                "campaign": {
                    "id": str(campaign.id),
                    "name": campaign.name,
                    "status": campaign.status,
                    "current_spend": float(campaign.current_spend),
                    "budget_limit": float(campaign.budget_limit)
                },
                "content": {
                    "raw_content": raw_content_count,
                    "processed_content": processed_content_count,
                    "processing_rate": (processed_content_count / raw_content_count * 100) if raw_content_count > 0 else 0
                },
                "insights": {
                    "total": insights_count,
                    "validated": validated_insights_count,
                    "validation_rate": (validated_insights_count / insights_count * 100) if insights_count > 0 else 0
                },
                "influencers": {
                    "identified": influencers_count
                },
                "activity": {
                    "recent_actions": recent_activity
                }
            }
        except Campaign.DoesNotExist:
            return {
                "success": False,
                "error": f"Campaign {campaign_id} not found"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run(self, campaign_id: str) -> Dict[str, Any]:
        """Synchronous version of campaign stats retrieval."""
        return asyncio.run(self._arun(campaign_id))


# Tool registry for easy access
LANGGRAPH_TOOLS = {
    "database_query": DatabaseQueryTool(),
    "content_search": ContentSearchTool(),
    "create_insight": InsightCreationTool(),
    "create_audit_log": AuditLogTool(),
    "get_campaign_stats": CampaignStatsTool(),
    # New RAG tools
    "hybrid_rag": hybrid_rag_tool,
    "vector_search": vector_search_tool,
    "hybrid_search": hybrid_search_tool,
    "brand_analytics": brand_analytics_tool,
    "community_query": community_query_tool,
    "influencer_query": influencer_query_tool,
    "pain_point_analysis": pain_point_analysis_tool,
    "campaign_analytics": campaign_analytics_tool,
    "trend_analysis": trend_analysis_tool,
}


def get_tools_for_node(node_name: str) -> List[BaseTool]:
    """Get the appropriate tools for a specific LangGraph node."""
    tool_mappings = {
        "scout": ["database_query", "create_audit_log"],
        "cleaner": ["database_query", "create_audit_log"],
        "analyst": ["database_query", "content_search", "create_insight", "create_audit_log"],
        "chatbot": [
            "hybrid_rag",  # Primary RAG tool
            "vector_search",  # Semantic search
            "hybrid_search",  # Combined search
            "brand_analytics",  # Brand KPIs
            "community_query",  # Community metrics
            "influencer_query",  # Influencer analytics
            "pain_point_analysis",  # Pain point trends
            "campaign_analytics",  # Campaign performance
            "trend_analysis",  # Temporal trends
            "get_campaign_stats",  # Legacy support
            "content_search",  # Legacy support
        ],
        "orchestrator": ["database_query", "get_campaign_stats", "create_audit_log"],
    }

    tools = []
    for tool_name in tool_mappings.get(node_name, []):
        if tool_name in LANGGRAPH_TOOLS:
            tools.append(LANGGRAPH_TOOLS[tool_name])

    return tools


def create_sql_query_tool() -> QuerySQLDataBaseTool:
    """Create a SQL database query tool using LangChain's SQLDatabase utility."""
    try:
        # Create database URL from Django settings
        db_config = settings.DATABASES['default']
        if db_config['ENGINE'] == 'django.db.backends.postgresql':
            db_url = f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
        else:
            db_url = f"sqlite:///{db_config['NAME']}"

        db = SQLDatabase.from_uri(db_url)
        return QuerySQLDataBaseTool(db=db)
    except Exception as e:
        print(f"Failed to create SQL query tool: {e}")
        return None
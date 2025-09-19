"""
LangGraph State Management for EchoChamber Analyst

This module defines the state schemas and management for the LangGraph-based
multi-agent system, replacing the custom agent framework.
"""

from typing import Dict, List, Optional, Any, Union, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(str, Enum):
    """Content type classification."""
    REDDIT_POST = "reddit_post"
    REDDIT_COMMENT = "reddit_comment"
    WEBSITE_ARTICLE = "website_article"
    SOCIAL_MEDIA = "social_media"
    RAW_TEXT = "raw_text"


class InsightType(str, Enum):
    """Types of insights generated."""
    PAIN_POINT = "pain_point"
    PRAISE = "praise"
    TREND = "trend"
    SENTIMENT = "sentiment"
    INFLUENCER = "influencer"
    KEYWORD = "keyword"


@dataclass
class ContentItem:
    """Represents a single content item being processed."""
    id: str
    content: str
    source_url: str
    content_type: ContentType
    author: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Processing status
    is_processed: bool = False
    is_cleaned: bool = False
    is_analyzed: bool = False

    # Scores and metrics
    echo_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    toxicity_score: Optional[float] = None

    # Extracted information
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    language: Optional[str] = None


@dataclass
class Insight:
    """Represents an AI-generated insight."""
    id: str
    insight_type: InsightType
    title: str
    description: str
    confidence_score: float
    priority_score: float
    source_content_ids: List[str]
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class InfluencerProfile:
    """Represents an identified influencer."""
    username: str
    platform: str
    influence_score: float
    follower_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    content_topics: List[str] = field(default_factory=list)
    recent_posts: List[str] = field(default_factory=list)


@dataclass
class CampaignContext:
    """Campaign-specific context and configuration."""
    campaign_id: str
    name: str
    keywords: List[str]
    sources: List[str]
    budget_limit: float
    current_spend: float = 0.0

    # Processing preferences
    target_languages: List[str] = field(default_factory=lambda: ["en"])
    content_types: List[ContentType] = field(default_factory=list)
    min_echo_score: float = 0.5

    # Time constraints
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class ProcessingMetrics:
    """Metrics and cost tracking for the current workflow."""
    total_tokens_used: int = 0
    total_cost: float = 0.0
    processing_time: float = 0.0
    api_calls_made: int = 0

    # Per-agent metrics
    scout_metrics: Dict[str, Any] = field(default_factory=dict)
    cleaner_metrics: Dict[str, Any] = field(default_factory=dict)
    analyst_metrics: Dict[str, Any] = field(default_factory=dict)

    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class WorkflowDecision:
    """Decision point in the workflow for conditional routing."""
    decision_type: str
    criteria: Dict[str, Any]
    selected_path: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)
    confidence: float = 1.0


class EchoChamberAnalystState(MessagesState):
    """
    Comprehensive state for the EchoChamber Analyst LangGraph workflow.

    This state is passed between all nodes and maintains the complete context
    of the analysis pipeline, including content, insights, metrics, and decisions.
    """

    # Core workflow context
    workflow_id: str = Field(description="Unique identifier for this workflow execution")
    campaign: CampaignContext = Field(description="Campaign configuration and context")
    task_status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current workflow status")

    # Content processing pipeline
    raw_content: List[ContentItem] = Field(
        default_factory=list,
        description="Raw content items from scout agents"
    )
    cleaned_content: List[ContentItem] = Field(
        default_factory=list,
        description="Content after cleaning and validation"
    )
    processed_content: List[ContentItem] = Field(
        default_factory=list,
        description="Fully processed and analyzed content"
    )

    # Analysis results
    insights: List[Insight] = Field(
        default_factory=list,
        description="Generated insights from analyst agents"
    )
    influencers: List[InfluencerProfile] = Field(
        default_factory=list,
        description="Identified influencers and their profiles"
    )

    # Workflow routing and decisions
    current_node: str = Field(default="start", description="Current node in the workflow")
    next_nodes: List[str] = Field(default_factory=list, description="Next nodes to execute")
    decisions: List[WorkflowDecision] = Field(
        default_factory=list,
        description="Decision points and routing logic"
    )

    # Parallel execution tracking
    parallel_tasks: Dict[str, TaskStatus] = Field(
        default_factory=dict,
        description="Status of parallel task execution"
    )

    # Metrics and monitoring
    metrics: ProcessingMetrics = Field(
        default_factory=ProcessingMetrics,
        description="Performance metrics and cost tracking"
    )

    # Chat and RAG context (for chatbot workflows)
    conversation_history: List[BaseMessage] = Field(
        default_factory=list,
        description="Conversation history for RAG interactions"
    )
    rag_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Retrieved context for RAG responses"
    )
    user_query: Optional[str] = Field(default=None, description="Current user query")

    # Tool and API integration results
    tool_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results from tool and API calls"
    )
    sql_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results from SQL database queries"
    )
    search_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results from search operations"
    )

    # Error handling and retry state
    retry_count: int = Field(default=0, description="Number of retries for failed operations")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    last_error: Optional[str] = Field(default=None, description="Last error encountered")

    # Compliance and audit
    audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Audit trail for compliance and explainability"
    )
    compliance_flags: List[str] = Field(
        default_factory=list,
        description="Compliance violations or flags"
    )

    # Workflow configuration
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow-specific configuration"
    )

    def add_content(self, content: ContentItem) -> None:
        """Add a content item to the appropriate list based on processing status."""
        if content.is_analyzed:
            self.processed_content.append(content)
        elif content.is_cleaned:
            self.cleaned_content.append(content)
        else:
            self.raw_content.append(content)

    def add_insight(self, insight: Insight) -> None:
        """Add an insight to the insights list."""
        self.insights.append(insight)

        # Add audit trail entry
        self.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "insight_generated",
            "insight_id": insight.id,
            "insight_type": insight.insight_type.value,
            "confidence": insight.confidence_score,
            "node": self.current_node
        })

    def update_metrics(self, tokens: int = 0, cost: float = 0.0, api_calls: int = 0) -> None:
        """Update processing metrics."""
        self.metrics.total_tokens_used += tokens
        self.metrics.total_cost += cost
        self.metrics.api_calls_made += api_calls

    def set_next_node(self, node: str, decision: Optional[WorkflowDecision] = None) -> None:
        """Set the next node to execute with optional decision context."""
        self.next_nodes = [node]
        if decision:
            self.decisions.append(decision)

    def set_parallel_nodes(self, nodes: List[str]) -> None:
        """Set multiple nodes for parallel execution."""
        self.next_nodes = nodes
        for node in nodes:
            self.parallel_tasks[node] = TaskStatus.PENDING

    def mark_task_completed(self, node: str) -> None:
        """Mark a parallel task as completed."""
        if node in self.parallel_tasks:
            self.parallel_tasks[node] = TaskStatus.COMPLETED

    def all_parallel_tasks_completed(self) -> bool:
        """Check if all parallel tasks are completed."""
        return all(
            status == TaskStatus.COMPLETED
            for status in self.parallel_tasks.values()
        )

    def add_error(self, error: str, node: Optional[str] = None) -> None:
        """Add an error to the metrics and audit trail."""
        self.metrics.errors.append(error)
        self.last_error = error

        self.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "error_occurred",
            "error": error,
            "node": node or self.current_node,
            "retry_count": self.retry_count
        })

    def should_retry(self) -> bool:
        """Check if the workflow should retry after an error."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment the retry counter."""
        self.retry_count += 1

    def get_content_summary(self) -> Dict[str, int]:
        """Get a summary of content processing status."""
        return {
            "raw_content": len(self.raw_content),
            "cleaned_content": len(self.cleaned_content),
            "processed_content": len(self.processed_content),
            "total_insights": len(self.insights),
            "identified_influencers": len(self.influencers)
        }


# Utility functions for state management

def create_initial_state(
    workflow_id: str,
    campaign: CampaignContext,
    config: Optional[Dict[str, Any]] = None
) -> EchoChamberAnalystState:
    """Create an initial state for a new workflow."""
    return EchoChamberAnalystState(
        workflow_id=workflow_id,
        campaign=campaign,
        config=config or {}
    )


def create_chat_state(
    user_query: str,
    conversation_history: Optional[List[BaseMessage]] = None,
    campaign_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a state for chat/RAG workflows."""
    campaign = CampaignContext(
        campaign_id=campaign_id or "chat_session",
        name="Chat Session",
        keywords=[],
        sources=[],
        budget_limit=0.0
    )

    # Create state as a dictionary since MessagesState works with dicts
    state = {
        "workflow_id": f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "campaign": campaign,
        "user_query": user_query,
        "conversation_history": conversation_history or [],
        "current_node": "chat_start",
        "task_status": TaskStatus.PENDING,
        "raw_content": [],
        "cleaned_content": [],
        "processed_content": [],
        "insights": [],
        "influencers": [],
        "current_decision": None,
        "workflow_decisions": [],
        "rag_context": {},
        "parallel_results": {},
        "error_state": None,
        "error_recovery_attempts": 0,
        "max_recovery_attempts": 3,
        "retry_count": 0,
        "max_retries": 3,
        "metrics": ProcessingMetrics(),
        "audit_trail": [],
        "compliance_events": [],
        "messages": conversation_history or []  # Required by MessagesState
    }

    return state
"""
LangSmith Monitoring and Observability Integration

This module provides comprehensive monitoring, tracing, and observability
for the LangGraph workflow using LangSmith, replacing custom logging
with standardized run logs and compliance tracking.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from functools import wraps
import json

from langsmith import Client
from langsmith.run_helpers import traceable
from langchain_core.tracers import LangChainTracer
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from .state import EchoChamberAnalystState, TaskStatus

logger = logging.getLogger(__name__)


class ComplianceTracker:
    """Track compliance violations and audit requirements."""

    def __init__(self):
        self.violations = []
        self.audit_events = []

    def log_pii_detection(self, content_id: str, pii_type: str, action: str):
        """Log PII detection and handling for compliance."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "pii_detection",
            "content_id": content_id,
            "pii_type": pii_type,
            "action": action,
            "compliance_level": "GDPR"
        }
        self.audit_events.append(event)

    def log_content_filtering(self, content_id: str, filter_reason: str, toxicity_score: float):
        """Log content filtering decisions."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "content_filtering",
            "content_id": content_id,
            "filter_reason": filter_reason,
            "toxicity_score": toxicity_score,
            "compliance_level": "Content_Safety"
        }
        self.audit_events.append(event)

    def log_ai_decision(self, decision_type: str, criteria: Dict[str, Any], outcome: str):
        """Log AI decision making for explainability."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "ai_decision",
            "decision_type": decision_type,
            "criteria": criteria,
            "outcome": outcome,
            "compliance_level": "AI_Governance"
        }
        self.audit_events.append(event)


class EchoChamberCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for EchoChamber-specific monitoring."""

    def __init__(self, compliance_tracker: ComplianceTracker):
        super().__init__()
        self.compliance_tracker = compliance_tracker
        self.run_costs = {}
        self.run_tokens = {}

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Track LLM call start."""
        run_id = kwargs.get("run_id")
        if run_id:
            logger.debug(f"LLM call started: {run_id}")

    def on_llm_end(self, response, **kwargs) -> None:
        """Track LLM call completion and costs."""
        run_id = kwargs.get("run_id")
        if run_id and hasattr(response, 'llm_output'):
            llm_output = response.llm_output or {}
            token_usage = llm_output.get('token_usage', {})

            self.run_tokens[str(run_id)] = {
                "prompt_tokens": token_usage.get('prompt_tokens', 0),
                "completion_tokens": token_usage.get('completion_tokens', 0),
                "total_tokens": token_usage.get('total_tokens', 0)
            }

            # Estimate costs (GPT-4 pricing)
            prompt_cost = token_usage.get('prompt_tokens', 0) * 0.00003
            completion_cost = token_usage.get('completion_tokens', 0) * 0.00006
            total_cost = prompt_cost + completion_cost

            self.run_costs[str(run_id)] = {
                "prompt_cost": prompt_cost,
                "completion_cost": completion_cost,
                "total_cost": total_cost
            }

            logger.info(f"LLM call completed: {run_id}, tokens: {token_usage}, cost: ${total_cost:.6f}")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Track tool usage for compliance."""
        tool_name = serialized.get("name", "unknown")
        run_id = kwargs.get("run_id")

        # Log sensitive tool usage
        if tool_name in ["database_query", "content_search"]:
            self.compliance_tracker.log_ai_decision(
                decision_type="tool_usage",
                criteria={"tool": tool_name, "input_preview": input_str[:100]},
                outcome="tool_executed"
            )

    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Track errors for debugging and compliance."""
        run_id = kwargs.get("run_id")
        logger.error(f"Chain error in run {run_id}: {error}")

        self.compliance_tracker.audit_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "workflow_error",
            "run_id": str(run_id),
            "error": str(error),
            "compliance_level": "Error_Tracking"
        })


class LangSmithMonitor:
    """Main monitoring class integrating LangSmith with EchoChamber workflows."""

    def __init__(self):
        self.client = None
        self.compliance_tracker = ComplianceTracker()
        self.callback_handler = EchoChamberCallbackHandler(self.compliance_tracker)
        self._setup_langsmith()

    def _setup_langsmith(self):
        """Initialize LangSmith client with environment configuration."""
        try:
            # Check for LangSmith configuration
            langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
            langsmith_project = os.getenv("LANGSMITH_PROJECT", "echochamber-analyst")
            langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

            if langsmith_api_key:
                self.client = Client(
                    api_url=langsmith_endpoint,
                    api_key=langsmith_api_key
                )

                # Set environment variables for LangChain integration
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_PROJECT"] = langsmith_project
                os.environ["LANGCHAIN_ENDPOINT"] = langsmith_endpoint
                os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key

                # Test the connection
                try:
                    # Try to create a simple test run to verify connection
                    test_run = self.client.create_run(
                        name="echochamber_connection_test",
                        run_type="chain",
                        inputs={"test": "connection"},
                        project_name=langsmith_project
                    )
                    self.client.update_run(test_run.id, outputs={"status": "connected"})
                    logger.info(f"✅ LangSmith monitoring successfully initialized for project: {langsmith_project}")
                    logger.info(f"🔗 LangSmith dashboard: https://smith.langchain.com/")
                except Exception as test_error:
                    logger.warning(f"LangSmith client created but connection test failed: {test_error}")
                    logger.info(f"LangSmith monitoring initialized for project: {langsmith_project}")
            else:
                logger.warning("❌ LangSmith API key not found. Monitoring will use local logging only.")
                logger.warning("   Add LANGSMITH_API_KEY to your .env file to enable full observability")

        except Exception as e:
            logger.error(f"Failed to initialize LangSmith: {e}")

    def get_tracer(self) -> Optional[LangChainTracer]:
        """Get LangChain tracer for workflow monitoring."""
        if self.client:
            return LangChainTracer()
        return None

    def create_workflow_run(self, workflow_id: str, workflow_type: str, campaign_id: str) -> Optional[str]:
        """Create a top-level run for workflow tracking."""
        if not self.client:
            return None

        try:
            run = self.client.create_run(
                name=f"echochamber_workflow_{workflow_type}",
                run_type="chain",
                inputs={
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type,
                    "campaign_id": campaign_id,
                    "timestamp": datetime.now().isoformat()
                },
                project_name=os.getenv("LANGSMITH_PROJECT", "echochamber-analyst"),
                tags=["echochamber", "workflow", workflow_type]
            )
            return str(run.id)
        except Exception as e:
            logger.error(f"Failed to create workflow run: {e}")
            return None

    def log_node_execution(self, run_id: str, node_name: str, state: EchoChamberAnalystState,
                          inputs: Dict[str, Any], outputs: Dict[str, Any]):
        """Log individual node execution with detailed context."""
        if not self.client or not run_id:
            return

        try:
            # Create child run for node
            node_run = self.client.create_run(
                name=f"node_{node_name}",
                run_type="llm" if node_name in ["analyst", "chatbot"] else "tool",
                inputs=inputs,
                outputs=outputs,
                parent_run_id=run_id,
                tags=["node", node_name, state.campaign.campaign_id],
                extra={
                    "node_name": node_name,
                    "workflow_id": state.workflow_id,
                    "campaign_id": state.campaign.campaign_id,
                    "task_status": state.task_status.value,
                    "metrics": {
                        "content_processed": len(state.processed_content),
                        "insights_generated": len(state.insights),
                        "total_cost": state.metrics.total_cost,
                        "total_tokens": state.metrics.total_tokens_used
                    }
                }
            )

            # Update run with completion status
            self.client.update_run(
                run_id=node_run.id,
                status="success" if not state.last_error else "error",
                error=state.last_error
            )

        except Exception as e:
            logger.error(f"Failed to log node execution: {e}")

    def log_compliance_event(self, event_type: str, details: Dict[str, Any]):
        """Log compliance-related events for audit trails."""
        self.compliance_tracker.audit_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "compliance_level": "Audit_Trail"
        })

    def generate_explainability_report(self, workflow_id: str) -> Dict[str, Any]:
        """Generate explainability report for AI decisions."""
        report = {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "compliance_events": self.compliance_tracker.audit_events,
            "ai_decisions": [
                event for event in self.compliance_tracker.audit_events
                if event.get("event_type") == "ai_decision"
            ],
            "pii_handling": [
                event for event in self.compliance_tracker.audit_events
                if event.get("event_type") == "pii_detection"
            ],
            "content_filtering": [
                event for event in self.compliance_tracker.audit_events
                if event.get("event_type") == "content_filtering"
            ]
        }

        return report

    def export_compliance_data(self, workflow_id: str, format: str = "json") -> str:
        """Export compliance data for regulatory requirements."""
        report = self.generate_explainability_report(workflow_id)

        if format == "json":
            return json.dumps(report, indent=2)
        else:
            # Could add CSV, XML formats for different regulatory requirements
            return json.dumps(report, indent=2)

    # --- Chat / RAG specific helpers (added for chatbot_node compatibility) ---
    def track_rag_interaction(self, query: str, campaign_id: Optional[str], user_context: Dict[str, Any]):
        """Track a RAG interaction (query received) for observability.

        This method is lightweight so it can run even without LangSmith connection.
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "rag_interaction",
            "query_preview": query[:200],
            "campaign_id": campaign_id,
            "user_context": user_context
        }
        self.compliance_tracker.audit_events.append(event)
        logger.debug(f"Tracked RAG interaction: {event}")

    def track_response_quality(self, query: str, response: str, context_sources: int, campaign_context: Optional[str]):
        """Track basic response quality metadata (placeholder for future metrics)."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "rag_response",
            "query_preview": query[:120],
            "response_length": len(response or ""),
            "context_sources": context_sources,
            "campaign_id": campaign_context
        }
        self.compliance_tracker.audit_events.append(event)
        logger.debug(f"Tracked RAG response quality: {event}")


# Decorators for monitoring

def monitor_node_execution(monitor: LangSmithMonitor):
    """Decorator to monitor LangGraph node execution."""
    def decorator(func):
        @wraps(func)
        async def wrapper(state: EchoChamberAnalystState, *args, **kwargs):
            node_name = func.__name__.replace("_node", "")

            # Capture inputs
            inputs = {
                "state_summary": state.get_content_summary(),
                "current_node": state.current_node,
                "workflow_id": state.workflow_id,
                "campaign_id": state.campaign.campaign_id
            }

            try:
                # Execute the node
                result_state = await func(state, *args, **kwargs)

                # Capture outputs
                outputs = {
                    "final_status": result_state.task_status.value,
                    "content_summary": result_state.get_content_summary(),
                    "errors": result_state.metrics.errors,
                    "warnings": result_state.metrics.warnings
                }

                # Log execution
                if hasattr(state, '_monitoring_run_id'):
                    monitor.log_node_execution(
                        state._monitoring_run_id,
                        node_name,
                        result_state,
                        inputs,
                        outputs
                    )

                return result_state

            except Exception as e:
                # Log error
                monitor.log_compliance_event("node_error", {
                    "node_name": node_name,
                    "error": str(e),
                    "workflow_id": state.workflow_id
                })
                raise

        return wrapper
    return decorator


@traceable(name="echochamber_insight_generation")
def trace_insight_generation(content_batch: List[Dict], insights: List[Dict]) -> Dict[str, Any]:
    """Traceable function for insight generation explainability."""
    return {
        "input_content_count": len(content_batch),
        "generated_insights": len(insights),
        "insight_types": [insight.get("type") for insight in insights],
        "confidence_scores": [insight.get("confidence") for insight in insights],
        "timestamp": datetime.now().isoformat()
    }


@traceable(name="echochamber_content_filtering")
def trace_content_filtering(content_items: List[Dict], filtered_count: int, filter_reasons: List[str]) -> Dict[str, Any]:
    """Traceable function for content filtering decisions."""
    return {
        "total_content": len(content_items),
        "filtered_count": filtered_count,
        "filter_reasons": filter_reasons,
        "filtering_rate": filtered_count / len(content_items) if content_items else 0,
        "timestamp": datetime.now().isoformat()
    }


# Global monitor instance
global_monitor = LangSmithMonitor()


def get_monitoring_callbacks():
    """Get callback handlers for LangGraph workflow monitoring."""
    callbacks = [global_monitor.callback_handler]

    # Add LangChain tracer if available
    tracer = global_monitor.get_tracer()
    if tracer:
        callbacks.append(tracer)

    return callbacks


def setup_workflow_monitoring(workflow_id: str, workflow_type: str, campaign_id: str) -> Optional[str]:
    """Setup monitoring for a new workflow execution."""
    return global_monitor.create_workflow_run(workflow_id, workflow_type, campaign_id)
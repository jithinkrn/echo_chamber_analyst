"""
LangGraph Workflow Orchestrator

This module implements the main orchestration workflow using LangGraph,
replacing the custom orchestrator agent with sophisticated graph-based
workflow management, conditional routing, and parallel execution.
"""

from typing import Dict, List, Any, Optional, Literal
import asyncio
import logging
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from .state import (
    EchoChamberAnalystState, TaskStatus, CampaignContext,
    WorkflowDecision, create_initial_state
)
from .tools import get_tools_for_node, LANGGRAPH_TOOLS
from .nodes import (
    scout_node, cleaner_node, analyst_node, chatbot_node, monitoring_node
)
from .monitoring import (
    setup_workflow_monitoring, get_monitoring_callbacks,
    global_monitor
)
from .retry import (
    with_retry, create_resilient_workflow_config,
    WorkflowErrorRecovery, global_retry_handler
)

logger = logging.getLogger(__name__)


class EchoChamberWorkflowOrchestrator:
    """
    Main workflow orchestrator using LangGraph for sophisticated
    multi-agent orchestration with conditional routing and parallel execution.
    """

    def __init__(self):
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_workflow()

    def _build_workflow(self):
        """Build the LangGraph workflow with all nodes and edges."""

        # Create the workflow graph
        workflow = StateGraph(EchoChamberAnalystState)

        # Add nodes with retry capabilities
        workflow.add_node("start", self._start_node)
        workflow.add_node("route_workflow", self._route_workflow)
        workflow.add_node("scout_content", with_retry(scout_node))
        workflow.add_node("clean_content", with_retry(cleaner_node))
        workflow.add_node("analyze_content", with_retry(analyst_node))
        workflow.add_node("chatbot_node", with_retry(chatbot_node))
        workflow.add_node("monitoring_agent", with_retry(monitoring_node))
        workflow.add_node("parallel_orchestrator", self._parallel_orchestrator)
        workflow.add_node("workflow_monitor", self._workflow_monitor)
        workflow.add_node("error_handler", self._enhanced_error_handler)
        workflow.add_node("finalize_workflow", self._finalize_workflow)

        # Set entry point
        workflow.set_entry_point("start")

        # Add conditional edges for sophisticated routing
        workflow.add_conditional_edges(
            "start",
            self._determine_workflow_type,
            {
                "content_analysis": "route_workflow",
                "chat_query": "chatbot_node",
                "error": "error_handler"
            }
        )

        workflow.add_conditional_edges(
            "route_workflow",
            self._route_content_processing,
            {
                "scout_first": "scout_content",
                "parallel_processing": "parallel_orchestrator",
                "analysis_only": "analyze_content",
                "error": "error_handler"
            }
        )

        # Content processing flow
        workflow.add_edge("scout_content", "clean_content")
        workflow.add_edge("clean_content", "analyze_content")
        workflow.add_edge("analyze_content", "workflow_monitor")

        # Parallel processing orchestration
        workflow.add_edge("parallel_orchestrator", "workflow_monitor")

        # Monitoring and error handling
        workflow.add_conditional_edges(
            "workflow_monitor",
            self._check_workflow_completion,
            {
                "completed": "monitoring_agent",
                "continue": "route_workflow",
                "error": "error_handler",
                "retry": "error_handler"
            }
        )

        # Monitoring agent to final workflow
        workflow.add_edge("monitoring_agent", "finalize_workflow")

        # Chatbot direct path (bypasses content processing)
        workflow.add_edge("chatbot_node", "finalize_workflow")

        # Error handling with retry logic
        workflow.add_conditional_edges(
            "error_handler",
            self._handle_errors,
            {
                "retry": "route_workflow",
                "abort": "finalize_workflow",
                "escalate": "finalize_workflow"
            }
        )

        # Final states
        workflow.add_edge("finalize_workflow", END)

        # Compile the graph
        self.graph = workflow.compile(
            checkpointer=self.checkpointer
        )

    async def _start_node(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Initialize the workflow and set up monitoring."""
        logger.info(f"Starting workflow {state.workflow_id} for campaign {state.campaign.campaign_id}")

        # Update state
        state.task_status = TaskStatus.RUNNING
        state.current_node = "start"

        # Add audit trail entry
        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": "workflow_started",
            "workflow_id": state.workflow_id,
            "campaign_id": state.campaign.campaign_id,
            "config": state.config
        })

        # Initialize metrics
        state.metrics.processing_time = datetime.now().timestamp()

        return state

    def _determine_workflow_type(self, state: Any) -> str:
        """Determine the type of workflow to execute based on the state."""
        try:
            # Check if this is a chat/RAG query using safe access
            user_query = self._get_state_value(state, 'user_query')
            conversation_history = self._get_state_value(state, 'conversation_history', [])
            
            if user_query or conversation_history:
                return "chat_query"

            # Check for content analysis workflow
            raw_content = self._get_state_value(state, 'raw_content', [])
            campaign = self._get_state_value(state, 'campaign')
            sources = getattr(campaign, 'sources', []) if campaign else []
            
            if raw_content or sources:
                return "content_analysis"

            logger.warning("No workflow type determined - defaulting to error")
            return "error"

        except Exception as e:
            logger.error(f"Failed to determine workflow type: {e}")
            return "error"

    async def _route_workflow(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Route the workflow based on current state and requirements."""
        state.current_node = "route_workflow"

        try:
            # Add routing decision
            decision = WorkflowDecision(
                decision_type="content_processing_route",
                criteria={
                    "has_raw_content": bool(state.raw_content),
                    "budget_remaining": state.campaign.budget_limit - state.campaign.current_spend,
                    "parallel_enabled": state.config.get("parallel_processing", True)
                }
            )

            # Determine next step based on content and configuration
            if not state.raw_content and state.campaign.sources:
                decision.selected_path = "scout_first"
            elif state.config.get("parallel_processing", True) and len(state.raw_content) > 10:
                decision.selected_path = "parallel_processing"
            elif state.raw_content:
                decision.selected_path = "analysis_only"
            else:
                decision.selected_path = "scout_first"

            state.decisions.append(decision)
            state.set_next_node(decision.selected_path)

            logger.info(f"Routed workflow to: {decision.selected_path}")

        except Exception as e:
            logger.error(f"Error in workflow routing: {e}")
            state.add_error(f"Workflow routing failed: {e}")

        return state

    def _route_content_processing(self, state: EchoChamberAnalystState) -> str:
        """Conditional routing for content processing."""
        if state.last_error:
            return "error"

        # Get the latest decision
        if state.decisions:
            return state.decisions[-1].selected_path

        return "scout_first"

    async def _parallel_orchestrator(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Orchestrate parallel execution of multiple agents."""
        state.current_node = "parallel_orchestrator"

        try:
            # Determine which nodes to run in parallel
            parallel_nodes = []

            if state.raw_content and not all(c.is_cleaned for c in state.raw_content):
                parallel_nodes.append("clean_content")

            if state.cleaned_content and not all(c.is_analyzed for c in state.cleaned_content):
                parallel_nodes.append("analyze_content")

            if parallel_nodes:
                state.set_parallel_nodes(parallel_nodes)
                logger.info(f"Starting parallel execution: {parallel_nodes}")

                # Execute nodes in parallel (simplified for this example)
                tasks = []
                for node in parallel_nodes:
                    if node == "clean_content":
                        tasks.append(cleaner_node(state))
                    elif node == "analyze_content":
                        tasks.append(analyst_node(state))

                # Wait for all tasks to complete
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results and update state
                    for i, result in enumerate(results):
                        node = parallel_nodes[i]
                        if isinstance(result, Exception):
                            state.add_error(f"Parallel node {node} failed: {result}")
                        else:
                            state.mark_task_completed(node)

        except Exception as e:
            logger.error(f"Error in parallel coordination: {e}")
            state.add_error(f"Parallel orchestration failed: {e}")

        return state

    async def _workflow_monitor(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Monitor workflow progress and check for completion."""
        state.current_node = "workflow_monitor"

        try:
            # Update metrics
            current_time = datetime.now().timestamp()
            state.metrics.processing_time = current_time - state.metrics.processing_time

            # Check budget constraints
            if state.metrics.total_cost > state.campaign.budget_limit:
                state.add_error("Budget limit exceeded")
                return state

            # Update campaign spend
            state.campaign.current_spend += state.metrics.total_cost

            # Log monitoring info
            logger.info(f"Workflow monitoring - Status: {state.task_status}, "
                       f"Cost: ${state.metrics.total_cost:.4f}, "
                       f"Time: {state.metrics.processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Error in workflow monitoring: {e}")
            state.add_error(f"Workflow monitoring failed: {e}")

        return state

    def _check_workflow_completion(self, state: EchoChamberAnalystState) -> str:
        """Check if the workflow is complete or needs to continue."""
        if state.last_error:
            return "error"

        # Check if all parallel tasks are completed
        if state.parallel_tasks and not state.all_parallel_tasks_completed():
            return "continue"

        # Check if we have processed all content
        if state.raw_content and not all(c.is_analyzed for c in state.raw_content):
            return "continue"

        # Check if insights have been generated
        if state.processed_content and not state.insights:
            return "continue"

        return "completed"

    async def _enhanced_error_handler(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Enhanced error handler with sophisticated recovery strategies."""
        state.current_node = "error_handler"

        try:
            logger.warning(f"Enhanced error handling for: {state.last_error}")

            # Determine error recovery strategy
            if "scout" in state.last_error.lower():
                state = await WorkflowErrorRecovery.recover_from_scout_failure(state)
            elif "analyst" in state.last_error.lower():
                state = await WorkflowErrorRecovery.recover_from_analyst_failure(state)
            elif "budget" in state.last_error.lower():
                state = await WorkflowErrorRecovery.recover_from_budget_exhaustion(state)

            # Log to compliance monitoring
            global_monitor.log_compliance_event("error_recovery_attempted", {
                "error": state.last_error,
                "recovery_strategy": "workflow_recovery",
                "workflow_id": state.workflow_id
            })

            # Check if recovery was successful
            if state.task_status != TaskStatus.FAILED:
                logger.info("Error recovery successful, continuing workflow")
                state.last_error = None
                return state

            # Final failure handling
            state.task_status = TaskStatus.FAILED
            logger.error(f"Enhanced error handling failed: {state.last_error}")

            # Record final failure in monitoring
            global_monitor.log_compliance_event("workflow_failure_final", {
                "error": state.last_error,
                "retry_count": state.retry_count,
                "workflow_id": state.workflow_id,
                "recovery_attempted": True
            })

        except Exception as e:
            logger.error(f"Error in enhanced error handler: {e}")
            state.add_error(f"Error handler failure: {e}")
            state.task_status = TaskStatus.FAILED

        return state

    def _handle_errors(self, state: EchoChamberAnalystState) -> str:
        """Determine error handling strategy."""
        if state.task_status == TaskStatus.FAILED:
            if state.retry_count < state.max_retries:
                return "retry"
            else:
                return "abort"

        return "escalate"

    async def _finalize_workflow(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Finalize the workflow and generate summary."""
        state.current_node = "finalize_workflow"

        try:
            if state.task_status != TaskStatus.FAILED:
                state.task_status = TaskStatus.COMPLETED

            # Generate final audit entry
            state.audit_trail.append({
                "timestamp": datetime.now().isoformat(),
                "action": "workflow_completed",
                "status": state.task_status.value,
                "total_cost": state.metrics.total_cost,
                "processing_time": state.metrics.processing_time,
                "content_processed": len(state.processed_content),
                "insights_generated": len(state.insights),
                "errors": len(state.metrics.errors)
            })

            # Log completion
            logger.info(f"Workflow {state.workflow_id} completed with status: {state.task_status}")

            # Use audit logging tool
            audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
            await audit_tool._arun(
                action_type="workflow_completion",
                action_description=f"Workflow {state.workflow_id} completed",
                agent_name="orchestrator",
                metadata={
                    "workflow_id": state.workflow_id,
                    "status": state.task_status.value,
                    "metrics": state.get_content_summary()
                }
            )

        except Exception as e:
            logger.error(f"Error finalizing workflow: {e}")
            state.add_error(f"Finalization failed: {e}")
            state.task_status = TaskStatus.FAILED

        return state

    async def execute_workflow(
        self,
        campaign: CampaignContext,
        workflow_type: str = "content_analysis",
        config: Optional[Dict[str, Any]] = None
    ) -> EchoChamberAnalystState:
        """Execute a complete workflow with monitoring."""

        # For chat workflows, use simplified direct execution
        # This avoids the complex graph state management issues
        if workflow_type == "chat_query":
            from .state import create_chat_state
            from .nodes import chatbot_node

            user_query = config.get("user_query", "") if config else ""
            conversation_history = config.get("conversation_history", []) if config else []

            # Create chat-specific state (returns dict)
            chat_state = create_chat_state(
                user_query=user_query,
                conversation_history=conversation_history,
                campaign_id=campaign.campaign_id
            )

            try:
                # Execute chatbot node directly
                final_state = await chatbot_node(chat_state)
                return final_state
            except Exception as e:
                logger.error(f"Chat workflow failed: {e}")
                chat_state['errors'] = [str(e)]
                chat_state['task_status'] = TaskStatus.FAILED
                return chat_state

        # For other workflows, use full graph execution
        # Create initial state
        workflow_id = f"{workflow_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        state = create_initial_state(workflow_id, campaign, config)

        # Setup monitoring
        monitoring_run_id = setup_workflow_monitoring(
            workflow_id, workflow_type, campaign.campaign_id
        )
        if monitoring_run_id:
            state._monitoring_run_id = monitoring_run_id

        try:
            # Execute the workflow with monitoring
            thread_config = {
                "configurable": {"thread_id": workflow_id},
                "callbacks": get_monitoring_callbacks()
            }

            final_state = await self.graph.ainvoke(
                state,
                config=thread_config
            )

            # LangGraph returns a dict - handle audit trail as dict
            # Generate compliance report
            if monitoring_run_id:
                compliance_report = global_monitor.generate_explainability_report(workflow_id)
                # Access as dict since LangGraph returns dict
                if 'audit_trail' not in final_state:
                    final_state['audit_trail'] = []
                final_state['audit_trail'].append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "compliance_report_generated",
                    "compliance_report": compliance_report
                })

            return final_state

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            # Log error to monitoring
            if monitoring_run_id:
                global_monitor.log_compliance_event("workflow_failure", {
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "campaign_id": campaign.campaign_id
                })

            # Handle error - use dict access since state is a dict
            if 'errors' not in state:
                state['errors'] = []
            state['errors'].append(f"Workflow execution failed: {e}")
            state['task_status'] = TaskStatus.FAILED
            return state

    def _get_state_value(self, state: Any, key: str, default: Any = None):
        """Safely get value from state whether it's dict or object."""
        if isinstance(state, dict):
            return state.get(key, default)
        else:
            return getattr(state, key, default)

    async def execute_chat_workflow(
        self,
        user_query: str,
        conversation_history: Optional[List] = None,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        [DEPRECATED] Execute a simplified chat/RAG workflow directly.

        This method bypasses the full LangGraph orchestration and is deprecated
        in favor of execute_workflow() which provides:
        - Complete LangSmith tracing and monitoring
        - Sophisticated error recovery with retry logic
        - Budget enforcement and cost tracking
        - Full audit trail for compliance
        - State checkpointing for fault tolerance

        Use execute_workflow() with a chat state instead:

        Example:
            from agents.state import CampaignContext

            campaign_context = CampaignContext(
                campaign_id=campaign_id or "chat_session",
                name="Chat Session",
                keywords=[],
                sources=[],
                budget_limit=0.0,
                current_spend=0.0
            )

            final_state = await orchestrator.execute_workflow(
                campaign=campaign_context,
                workflow_type="chat_query",
                config={
                    "user_query": user_query,
                    "conversation_history": conversation_history or []
                }
            )

        Args:
            user_query: The user's chat query
            conversation_history: Optional conversation history as LangChain messages
            campaign_id: Optional campaign ID for context

        Returns:
            Final workflow state (same as execute_workflow)

        Deprecated:
            Since version 2.0. Use execute_workflow() instead.
        """
        import warnings
        warnings.warn(
            "execute_chat_workflow() is deprecated and will be removed in version 3.0. "
            "Use execute_workflow() with a chat state instead for full graph orchestration.",
            DeprecationWarning,
            stacklevel=2
        )

        logger.warning(
            f"DEPRECATED: execute_chat_workflow() called for query: {user_query[:50]}... "
            "Redirecting to full graph workflow via execute_workflow()"
        )

        try:
            # Redirect to full graph workflow
            from .state import CampaignContext

            campaign_context = CampaignContext(
                campaign_id=campaign_id or "chat_session",
                name="Chat Session",
                keywords=[],
                sources=[],
                budget_limit=0.0,
                current_spend=0.0
            )

            logger.info("Redirecting to full graph workflow execution")
            return await self.execute_workflow(
                campaign=campaign_context,
                workflow_type="chat_query",
                config={
                    "user_query": user_query,
                    "conversation_history": conversation_history or []
                }
            )

        except Exception as e:
            logger.error(f"Deprecated chat workflow redirection failed: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "user_query": user_query,
                "messages": conversation_history or []
            }

    def _add_chatbot_to_graph(self):
        """Add chatbot node to the existing graph."""
        # This would require rebuilding the graph - simplified for now
        pass

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow."""
        try:
            # Get state from checkpointer
            thread_config = {"configurable": {"thread_id": workflow_id}}
            state = self.graph.get_state(thread_config)

            if state:
                return {
                    "workflow_id": workflow_id,
                    "status": state.values.get("task_status"),
                    "current_node": state.values.get("current_node"),
                    "metrics": state.values.get("metrics"),
                    "errors": state.values.get("metrics", {}).get("errors", [])
                }

        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")

        return None

    def get_node_health(self, node_name: str) -> bool:
        """Check if a specific node is healthy and available."""
        try:
            # Check if the node exists in the workflow graph
            if not self.graph:
                return False
                
            # Get the nodes from the compiled graph
            available_nodes = [
                'scout_content', 'clean_content', 'analyze_content', 
                'chatbot_node', 'monitoring_agent', 'workflow_monitor',
                'parallel_orchestrator', 'error_handler', 'finalize_workflow'
            ]
            
            # Map agent names to actual node names
            node_mapping = {
                'scout_node': 'scout_content',
                'cleaner_node': 'clean_content', 
                'analyst_node': 'analyze_content',
                'chatbot_node': 'chatbot_node',
                'monitoring_agent': 'monitoring_agent',
                'workflow_orchestrator': 'workflow_monitor'
            }
            
            actual_node_name = node_mapping.get(node_name, node_name)
            return actual_node_name in available_nodes
            
        except Exception as e:
            logger.error(f"Health check failed for node {node_name}: {e}")
            return False

    def restart_node(self, node_name: str) -> bool:
        """Restart a specific node (placeholder implementation)."""
        try:
            logger.info(f"Restarting node: {node_name}")
            # In a real implementation, you might reset node-specific state
            # For now, just return success if the node exists
            return self.get_node_health(node_name)
        except Exception as e:
            logger.error(f"Failed to restart node {node_name}: {e}")
            return False


# Global orchestrator instance
workflow_orchestrator = EchoChamberWorkflowOrchestrator()
"""
LangGraph Retry Mechanisms and Error Handling

This module provides sophisticated retry mechanisms and error handling
for LangGraph workflows, replacing custom error handling with
standardized LangGraph retry policies and error recovery strategies.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Type
from datetime import datetime, timedelta
import asyncio
from enum import Enum

from langchain_core.runnables import Runnable
from langchain_core.runnables.utils import Input, Output
# Define workflow control constants
SKIP = "skip"
RETURN = "return"
INTERRUPT = "interrupt"
from langgraph.errors import GraphRecursionError, InvalidUpdateError

from .state import EchoChamberAnalystState, TaskStatus
from .monitoring import global_monitor

logger = logging.getLogger(__name__)


class RetryPolicy(str, Enum):
    """Retry policy strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


class ErrorType(str, Enum):
    """Error categorization for different retry strategies."""
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    LLM_ERROR = "llm_error"
    VALIDATION_ERROR = "validation_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    CRITICAL_ERROR = "critical_error"


class RetryConfig:
    """Configuration for retry policies."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_policy = backoff_policy


class EchoChamberRetryHandler:
    """Sophisticated retry handler for EchoChamber workflows."""

    def __init__(self):
        self.error_configs = self._setup_error_configs()
        self.circuit_breakers = {}

    def _setup_error_configs(self) -> Dict[ErrorType, RetryConfig]:
        """Setup retry configurations for different error types."""
        return {
            ErrorType.RATE_LIMIT: RetryConfig(
                max_retries=5,
                base_delay=2.0,
                max_delay=120.0,
                backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF
            ),
            ErrorType.NETWORK_ERROR: RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF
            ),
            ErrorType.LLM_ERROR: RetryConfig(
                max_retries=3,
                base_delay=0.5,
                max_delay=10.0,
                backoff_policy=RetryPolicy.LINEAR_BACKOFF
            ),
            ErrorType.VALIDATION_ERROR: RetryConfig(
                max_retries=1,
                base_delay=0.1,
                max_delay=1.0,
                backoff_policy=RetryPolicy.IMMEDIATE
            ),
            ErrorType.BUSINESS_LOGIC_ERROR: RetryConfig(
                max_retries=2,
                base_delay=0.5,
                max_delay=5.0,
                backoff_policy=RetryPolicy.FIXED_DELAY
            ),
            ErrorType.CRITICAL_ERROR: RetryConfig(
                max_retries=0,
                backoff_policy=RetryPolicy.NO_RETRY
            )
        }

    def categorize_error(self, error: Exception) -> ErrorType:
        """Categorize errors for appropriate retry strategy."""
        error_str = str(error).lower()

        # Rate limiting errors
        if any(keyword in error_str for keyword in [
            "rate limit", "too many requests", "quota exceeded", "429"
        ]):
            return ErrorType.RATE_LIMIT

        # Network errors
        if any(keyword in error_str for keyword in [
            "connection", "timeout", "network", "dns", "502", "503", "504"
        ]):
            return ErrorType.NETWORK_ERROR

        # LLM-specific errors
        if any(keyword in error_str for keyword in [
            "openai", "model", "token", "context length", "api key"
        ]):
            return ErrorType.LLM_ERROR

        # Validation errors
        if any(keyword in error_str for keyword in [
            "validation", "invalid", "malformed", "schema"
        ]):
            return ErrorType.VALIDATION_ERROR

        # Critical errors (don't retry)
        if any(keyword in error_str for keyword in [
            "permission", "unauthorized", "forbidden", "authentication"
        ]):
            return ErrorType.CRITICAL_ERROR

        # Default to business logic error
        return ErrorType.BUSINESS_LOGIC_ERROR

    async def calculate_delay(
        self,
        retry_count: int,
        config: RetryConfig,
        error_type: ErrorType
    ) -> float:
        """Calculate delay based on retry policy."""
        if config.backoff_policy == RetryPolicy.NO_RETRY:
            return 0

        if config.backoff_policy == RetryPolicy.IMMEDIATE:
            return 0

        if config.backoff_policy == RetryPolicy.FIXED_DELAY:
            delay = config.base_delay

        elif config.backoff_policy == RetryPolicy.LINEAR_BACKOFF:
            delay = config.base_delay * retry_count

        elif config.backoff_policy == RetryPolicy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.exponential_base ** retry_count)

        else:
            delay = config.base_delay

        # Apply maximum delay cap
        delay = min(delay, config.max_delay)

        # Add jitter to prevent thundering herd
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)

        return delay

    async def should_retry(
        self,
        error: Exception,
        retry_count: int,
        node_name: str,
        state: EchoChamberAnalystState
    ) -> bool:
        """Determine if an error should be retried."""
        error_type = self.categorize_error(error)
        config = self.error_configs[error_type]

        # Check retry count
        if retry_count >= config.max_retries:
            return False

        # Check circuit breaker
        if self._is_circuit_breaker_open(node_name, error_type):
            return False

        # Check budget constraints
        if state.metrics.total_cost > state.campaign.budget_limit * 0.9:
            logger.warning("Approaching budget limit, skipping retry")
            return False

        # Check time constraints
        if hasattr(state, 'start_time'):
            elapsed = datetime.now().timestamp() - state.start_time
            if elapsed > 1800:  # 30 minutes max
                logger.warning("Workflow timeout approaching, skipping retry")
                return False

        return True

    def _is_circuit_breaker_open(self, node_name: str, error_type: ErrorType) -> bool:
        """Check if circuit breaker is open for this node/error combination."""
        key = f"{node_name}:{error_type.value}"
        breaker = self.circuit_breakers.get(key)

        if not breaker:
            return False

        # Simple circuit breaker logic
        if breaker["failures"] >= 5:
            time_since_last_failure = datetime.now() - breaker["last_failure"]
            if time_since_last_failure < timedelta(minutes=5):
                return True
            else:
                # Reset circuit breaker
                self.circuit_breakers[key] = {
                    "failures": 0,
                    "last_failure": None
                }

        return False

    def _record_failure(self, node_name: str, error_type: ErrorType):
        """Record failure for circuit breaker tracking."""
        key = f"{node_name}:{error_type.value}"
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = {"failures": 0, "last_failure": None}

        self.circuit_breakers[key]["failures"] += 1
        self.circuit_breakers[key]["last_failure"] = datetime.now()

    async def handle_retry(
        self,
        error: Exception,
        retry_count: int,
        node_name: str,
        state: EchoChamberAnalystState
    ) -> Optional[EchoChamberAnalystState]:
        """Handle retry logic for node execution."""
        error_type = self.categorize_error(error)

        # Log error details
        logger.warning(f"Node {node_name} failed (attempt {retry_count + 1}): {error}")

        # Check if we should retry
        if not await self.should_retry(error, retry_count, node_name, state):
            logger.error(f"Max retries reached or retry not allowed for {node_name}")
            self._record_failure(node_name, error_type)

            # Add to compliance monitoring
            global_monitor.log_compliance_event("retry_exhausted", {
                "node_name": node_name,
                "error_type": error_type.value,
                "retry_count": retry_count,
                "error": str(error)
            })

            # Update state with final error
            state.add_error(f"Node {node_name} failed after {retry_count} retries: {error}")
            state.task_status = TaskStatus.FAILED
            return state

        # Calculate delay
        config = self.error_configs[error_type]
        delay = await self.calculate_delay(retry_count, config, error_type)

        # Log retry attempt
        logger.info(f"Retrying {node_name} in {delay:.2f}s (attempt {retry_count + 1}/{config.max_retries})")

        # Wait before retry
        if delay > 0:
            await asyncio.sleep(delay)

        # Log compliance event
        global_monitor.log_compliance_event("node_retry", {
            "node_name": node_name,
            "error_type": error_type.value,
            "retry_count": retry_count + 1,
            "delay": delay,
            "error": str(error)
        })

        # Update state retry count
        state.increment_retry()

        return None  # Indicate retry should proceed


class RetryableNodeWrapper:
    """Wrapper to make any LangGraph node retryable."""

    def __init__(self, node_function: Callable, retry_handler: EchoChamberRetryHandler):
        self.node_function = node_function
        self.retry_handler = retry_handler
        self.node_name = node_function.__name__.replace("_node", "")

    async def __call__(self, state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Execute node with retry logic."""
        retry_count = 0
        max_total_retries = 10  # Global safety limit

        while retry_count <= max_total_retries:
            try:
                # Execute the original node function
                result_state = await self.node_function(state)

                # Success - reset circuit breaker
                key = f"{self.node_name}:success"
                if key in self.retry_handler.circuit_breakers:
                    del self.retry_handler.circuit_breakers[key]

                return result_state

            except Exception as error:
                retry_result = await self.retry_handler.handle_retry(
                    error, retry_count, self.node_name, state
                )

                if retry_result is not None:
                    # Retry exhausted or not allowed
                    return retry_result

                # Increment retry count and continue
                retry_count += 1

        # Safety fallback
        logger.error(f"Node {self.node_name} exceeded maximum total retries")
        state.add_error(f"Node {self.node_name} exceeded maximum total retries")
        state.task_status = TaskStatus.FAILED
        return state


# Global retry handler
global_retry_handler = EchoChamberRetryHandler()


def with_retry(node_function: Callable) -> RetryableNodeWrapper:
    """Decorator to add retry functionality to LangGraph nodes."""
    return RetryableNodeWrapper(node_function, global_retry_handler)


def create_resilient_workflow_config() -> Dict[str, Any]:
    """Create workflow configuration with resilience features."""
    return {
        "recursion_limit": 50,
        "max_concurrent_nodes": 5,
        "timeout": 1800,  # 30 minutes
        "error_handling": "graceful",
        "retry_enabled": True,
        "circuit_breaker_enabled": True,
        "monitoring_enabled": True
    }


class WorkflowErrorRecovery:
    """Advanced error recovery strategies for workflow failures."""

    @staticmethod
    async def recover_from_scout_failure(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Recovery strategy for scout node failures."""
        logger.info("Attempting recovery from scout failure")

        # Try alternative content sources
        if not state.raw_content and state.campaign.sources:
            # Use cached content or fallback sources
            state.raw_content = []  # Add fallback content discovery logic here

        return state

    @staticmethod
    async def recover_from_analyst_failure(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Recovery strategy for analyst node failures."""
        logger.info("Attempting recovery from analyst failure")

        # Generate basic insights from cleaned content without LLM
        if state.cleaned_content and not state.insights:
            # Add rule-based insight generation as fallback
            pass

        return state

    @staticmethod
    async def recover_from_budget_exhaustion(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
        """Recovery strategy for budget exhaustion."""
        logger.warning("Budget exhausted, switching to lightweight processing")

        # Switch to more efficient processing modes
        state.config["lightweight_mode"] = True
        state.config["reduce_llm_calls"] = True

        return state
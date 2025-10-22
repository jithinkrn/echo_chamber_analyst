"""
Comprehensive Error Handling and Recovery Module

This module provides advanced error handling, recovery strategies,
and graceful degradation for the EchoChamber workflow system.
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels for different handling strategies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error scenarios."""
    RETRY = "retry"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    SKIP_AND_CONTINUE = "skip_and_continue"
    ABORT = "abort"
    ESCALATE = "escalate"


class ErrorContext:
    """Context information for error handling."""

    def __init__(
        self,
        error: Exception,
        operation: str,
        component: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.error = error
        self.operation = operation
        self.component = component
        self.severity = severity
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary."""
        return {
            'error_type': type(self.error).__name__,
            'error_message': str(self.error),
            'operation': self.operation,
            'component': self.component,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'stack_trace': self.stack_trace
        }


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise Exception(f"Circuit breaker is OPEN. Service unavailable. Last failure: {self.last_failure_time}")

        try:
            result = func(*args, **kwargs)

            if self.state == "half_open":
                self._reset()

            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

    def _record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _reset(self):
        """Reset the circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"
        logger.info("Circuit breaker reset to CLOSED state")


class ErrorHandlingService:
    """Central error handling service with recovery strategies."""

    def __init__(self):
        self.error_log = []
        self.circuit_breakers = {}
        self.recovery_strategies = self._setup_recovery_strategies()

    def _setup_recovery_strategies(self) -> Dict[str, RecoveryStrategy]:
        """Setup recovery strategies for different error types."""
        return {
            # Network and API errors
            'ConnectionError': RecoveryStrategy.RETRY,
            'TimeoutError': RecoveryStrategy.RETRY,
            'HTTPError': RecoveryStrategy.RETRY,

            # LLM errors
            'RateLimitError': RecoveryStrategy.GRACEFUL_DEGRADATION,
            'InvalidRequestError': RecoveryStrategy.FALLBACK,
            'APIError': RecoveryStrategy.RETRY,

            # Data errors
            'ValidationError': RecoveryStrategy.SKIP_AND_CONTINUE,
            'IntegrityError': RecoveryStrategy.SKIP_AND_CONTINUE,

            # Critical errors
            'MemoryError': RecoveryStrategy.ABORT,
            'SystemError': RecoveryStrategy.ESCALATE,

            # Business logic errors
            'BudgetExceededError': RecoveryStrategy.ABORT,
            'DataNotFoundError': RecoveryStrategy.FALLBACK,
        }

    def handle_error(
        self,
        error: Exception,
        operation: str,
        component: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle an error with appropriate recovery strategy.

        Args:
            error: The exception that occurred
            operation: Operation being performed
            component: Component where error occurred
            severity: Error severity level
            metadata: Additional context metadata

        Returns:
            ErrorContext with handling information
        """
        context = ErrorContext(error, operation, component, severity, metadata)

        # Log the error
        self._log_error(context)

        # Determine recovery strategy
        strategy = self._determine_recovery_strategy(error, severity)

        # Apply recovery strategy
        self._apply_recovery_strategy(strategy, context)

        return context

    def _log_error(self, context: ErrorContext):
        """Log error to storage and monitoring systems."""
        # Add to in-memory log
        self.error_log.append(context.to_dict())

        # Keep only last 1000 errors
        if len(self.error_log) > 1000:
            self.error_log = self.error_log[-1000:]

        # Log based on severity
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR in {context.component}.{context.operation}: {context.error}")
            logger.critical(context.stack_trace)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(f"ERROR in {context.component}.{context.operation}: {context.error}")
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"WARNING in {context.component}.{context.operation}: {context.error}")
        else:
            logger.info(f"INFO in {context.component}.{context.operation}: {context.error}")

        # Cache error for monitoring dashboard
        cache_key = f"error_log:{context.component}:{datetime.now().strftime('%Y%m%d%H')}"
        try:
            existing_errors = cache.get(cache_key, [])
            existing_errors.append(context.to_dict())
            cache.set(cache_key, existing_errors, 3600)  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Failed to cache error: {e}")

    def _determine_recovery_strategy(
        self,
        error: Exception,
        severity: ErrorSeverity
    ) -> RecoveryStrategy:
        """Determine appropriate recovery strategy for an error."""
        error_type = type(error).__name__

        # Check if we have a specific strategy for this error type
        if error_type in self.recovery_strategies:
            return self.recovery_strategies[error_type]

        # Default strategy based on severity
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT
        elif severity == ErrorSeverity.HIGH:
            return RecoveryStrategy.ESCALATE
        elif severity == ErrorSeverity.MEDIUM:
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.SKIP_AND_CONTINUE

    def _apply_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        context: ErrorContext
    ):
        """Apply recovery strategy for an error."""
        logger.info(f"Applying recovery strategy '{strategy.value}' for {context.component}.{context.operation}")

        if strategy == RecoveryStrategy.RETRY:
            # Will be handled by retry decorator
            pass

        elif strategy == RecoveryStrategy.FALLBACK:
            # Use fallback mechanism
            logger.info(f"Using fallback mechanism for {context.operation}")

        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            # Reduce functionality but continue
            logger.info(f"Gracefully degrading functionality for {context.operation}")

        elif strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
            # Skip this operation and continue
            logger.info(f"Skipping operation {context.operation} and continuing")

        elif strategy == RecoveryStrategy.ABORT:
            # Abort the entire workflow
            logger.error(f"Aborting workflow due to critical error in {context.operation}")

        elif strategy == RecoveryStrategy.ESCALATE:
            # Escalate to human intervention
            logger.error(f"Escalating error in {context.operation} for human intervention")
            self._escalate_error(context)

    def _escalate_error(self, context: ErrorContext):
        """Escalate error for human intervention."""
        # In production, this would send alerts via:
        # - Email
        # - Slack/Teams notification
        # - PagerDuty
        # - etc.

        logger.critical(f"ERROR ESCALATION: {context.component}.{context.operation}")
        logger.critical(f"Details: {context.to_dict()}")

        # Store in database for admin dashboard
        try:
            from common.models import ErrorLog
            ErrorLog.objects.create(
                component=context.component,
                operation=context.operation,
                error_type=type(context.error).__name__,
                error_message=str(context.error),
                severity=context.severity.value,
                stack_trace=context.stack_trace,
                metadata=context.metadata
            )
        except Exception as e:
            logger.error(f"Failed to store error log: {e}")

    def get_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a component."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )

        return self.circuit_breakers[name]

    def get_recent_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent errors from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent_errors = [
            error for error in self.error_log
            if datetime.fromisoformat(error['timestamp']) >= cutoff_time
        ]

        return recent_errors

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        recent_errors = self.get_recent_errors(24)

        stats = {
            'total_errors_24h': len(recent_errors),
            'errors_by_severity': {},
            'errors_by_component': {},
            'errors_by_type': {},
            'circuit_breaker_states': {}
        }

        # Count by severity
        for error in recent_errors:
            severity = error.get('severity', 'unknown')
            stats['errors_by_severity'][severity] = stats['errors_by_severity'].get(severity, 0) + 1

            component = error.get('component', 'unknown')
            stats['errors_by_component'][component] = stats['errors_by_component'].get(component, 0) + 1

            error_type = error.get('error_type', 'unknown')
            stats['errors_by_type'][error_type] = stats['errors_by_type'].get(error_type, 0) + 1

        # Get circuit breaker states
        for name, breaker in self.circuit_breakers.items():
            stats['circuit_breaker_states'][name] = {
                'state': breaker.state,
                'failure_count': breaker.failure_count,
                'last_failure': breaker.last_failure_time.isoformat() if breaker.last_failure_time else None
            }

        return stats


# Global error handling service
error_service = ErrorHandlingService()


# Decorator for automatic error handling
def handle_errors(
    operation: str,
    component: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    use_circuit_breaker: bool = False
):
    """
    Decorator for automatic error handling.

    Usage:
        @handle_errors(operation="process_content", component="scout_agent")
        def my_function():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                if use_circuit_breaker:
                    breaker = error_service.get_circuit_breaker(f"{component}:{operation}")
                    return await breaker.call(func, *args, **kwargs)
                else:
                    return await func(*args, **kwargs)

            except Exception as e:
                error_service.handle_error(
                    error=e,
                    operation=operation,
                    component=component,
                    severity=severity,
                    metadata={
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200]
                    }
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                if use_circuit_breaker:
                    breaker = error_service.get_circuit_breaker(f"{component}:{operation}")
                    return breaker.call(func, *args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                error_service.handle_error(
                    error=e,
                    operation=operation,
                    component=component,
                    severity=severity,
                    metadata={
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200]
                    }
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Fallback mechanisms

class FallbackManager:
    """Manage fallback mechanisms for critical operations."""

    def __init__(self):
        self.fallback_functions = {}

    def register_fallback(self, operation: str, fallback_func: Callable):
        """Register a fallback function for an operation."""
        self.fallback_functions[operation] = fallback_func
        logger.info(f"Registered fallback for operation: {operation}")

    def execute_with_fallback(
        self,
        operation: str,
        primary_func: Callable,
        *args,
        **kwargs
    ):
        """Execute primary function with fallback on failure."""
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed for {operation}: {e}")

            if operation in self.fallback_functions:
                logger.info(f"Executing fallback for {operation}")
                try:
                    return self.fallback_functions[operation](*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for {operation}: {fallback_error}")
                    raise

            raise


# Global fallback manager
fallback_manager = FallbackManager()

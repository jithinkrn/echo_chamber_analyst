"""
Monitoring and Observability Integration for RAG System.

This module provides:
- LangSmith tracing for RAG queries
- Guardrails for query validation
- Performance metrics tracking
- Error monitoring and alerting
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from functools import wraps

from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import LangSmith (optional dependency)
try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    logger.warning("LangSmith not available. Install with: pip install langsmith")
    LANGSMITH_AVAILABLE = False

    # Create dummy decorator if LangSmith not available
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


class Guardrails:
    """
    Query validation and safety guardrails.

    Prevents:
    - Malformed queries
    - Injection attempts
    - Excessive load (rate limiting)
    - Sensitive data exposure
    """

    # Query length limits
    MIN_QUERY_LENGTH = 3
    MAX_QUERY_LENGTH = 500

    # Blocked patterns (simple injection prevention)
    BLOCKED_PATTERNS = [
        "'; DROP TABLE",
        "'; DELETE FROM",
        "<script>",
        "javascript:",
        "__import__",
        "eval(",
        "exec("
    ]

    # Rate limiting (in-memory, simple implementation)
    _query_counts = {}
    MAX_QUERIES_PER_MINUTE = 30

    @classmethod
    def validate_query(cls, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate user query against guardrails.

        Args:
            query: User's query string
            user_id: Optional user identifier for rate limiting

        Returns:
            Dictionary with validation result
        """
        # Check query length
        if len(query) < cls.MIN_QUERY_LENGTH:
            return {
                "valid": False,
                "error": f"Query too short. Minimum {cls.MIN_QUERY_LENGTH} characters required.",
                "code": "QUERY_TOO_SHORT"
            }

        if len(query) > cls.MAX_QUERY_LENGTH:
            return {
                "valid": False,
                "error": f"Query too long. Maximum {cls.MAX_QUERY_LENGTH} characters allowed.",
                "code": "QUERY_TOO_LONG"
            }

        # Check for blocked patterns
        query_upper = query.upper()
        for pattern in cls.BLOCKED_PATTERNS:
            if pattern.upper() in query_upper:
                logger.warning(f"Blocked pattern detected in query: {pattern}")
                return {
                    "valid": False,
                    "error": "Query contains potentially harmful content.",
                    "code": "BLOCKED_PATTERN"
                }

        # Rate limiting (simple in-memory implementation)
        if user_id:
            current_minute = int(time.time() / 60)
            key = f"{user_id}:{current_minute}"

            if key in cls._query_counts:
                cls._query_counts[key] += 1
                if cls._query_counts[key] > cls.MAX_QUERIES_PER_MINUTE:
                    return {
                        "valid": False,
                        "error": "Rate limit exceeded. Please wait before making more queries.",
                        "code": "RATE_LIMIT_EXCEEDED"
                    }
            else:
                # Clean up old entries
                cls._query_counts = {k: v for k, v in cls._query_counts.items()
                                    if k.split(':')[1] == str(current_minute)}
                cls._query_counts[key] = 1

        return {
            "valid": True,
            "code": "OK"
        }

    @classmethod
    def sanitize_output(cls, output: str) -> str:
        """
        Sanitize output to prevent sensitive data exposure.

        Args:
            output: Generated response text

        Returns:
            Sanitized output
        """
        # Remove potential API keys (simple pattern matching)
        import re

        # Pattern for API keys (basic heuristic)
        api_key_pattern = r'[a-zA-Z0-9_-]{32,}'
        output = re.sub(api_key_pattern, '[REDACTED]', output)

        # Remove email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        output = re.sub(email_pattern, '[EMAIL_REDACTED]', output)

        # Remove phone numbers (basic pattern)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        output = re.sub(phone_pattern, '[PHONE_REDACTED]', output)

        return output


class PerformanceMetrics:
    """
    Track performance metrics for RAG queries.

    Metrics:
    - Query execution time
    - Tool execution times
    - Cache hit rates
    - Result relevance scores
    """

    _metrics = []
    MAX_METRICS_STORED = 1000  # Keep last 1000 queries

    @classmethod
    def record_query(
        cls,
        query: str,
        execution_time: float,
        intent_type: str,
        tools_executed: List[str],
        result_count: int,
        success: bool,
        metadata: Dict[str, Any] = None
    ):
        """
        Record query execution metrics.

        Args:
            query: User query
            execution_time: Total execution time in seconds
            intent_type: Classified intent type
            tools_executed: List of tools that were executed
            result_count: Number of results returned
            success: Whether query succeeded
            metadata: Additional metadata
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "query_length": len(query),
            "execution_time": execution_time,
            "intent_type": intent_type,
            "tools_executed": tools_executed,
            "tool_count": len(tools_executed),
            "result_count": result_count,
            "success": success,
            "metadata": metadata or {}
        }

        cls._metrics.append(metric)

        # Keep only recent metrics
        if len(cls._metrics) > cls.MAX_METRICS_STORED:
            cls._metrics = cls._metrics[-cls.MAX_METRICS_STORED:]

        # Log slow queries
        if execution_time > 5.0:
            logger.warning(f"Slow query detected: {execution_time:.2f}s for query: {query[:100]}")

    @classmethod
    def get_statistics(cls, last_n: Optional[int] = None) -> Dict[str, Any]:
        """
        Get performance statistics.

        Args:
            last_n: Optional number of recent queries to analyze

        Returns:
            Dictionary with statistics
        """
        if not cls._metrics:
            return {
                "total_queries": 0,
                "message": "No metrics recorded yet"
            }

        metrics = cls._metrics[-last_n:] if last_n else cls._metrics

        total_queries = len(metrics)
        successful_queries = sum(1 for m in metrics if m["success"])
        failed_queries = total_queries - successful_queries

        execution_times = [m["execution_time"] for m in metrics]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0
        min_execution_time = min(execution_times) if execution_times else 0

        # Intent distribution
        intent_counts = {}
        for m in metrics:
            intent = m.get("intent_type", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        # Tool usage
        tool_counts = {}
        for m in metrics:
            for tool in m.get("tools_executed", []):
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate": round(successful_queries / total_queries, 3) if total_queries > 0 else 0,
            "execution_time": {
                "avg_seconds": round(avg_execution_time, 3),
                "max_seconds": round(max_execution_time, 3),
                "min_seconds": round(min_execution_time, 3)
            },
            "intent_distribution": intent_counts,
            "tool_usage": tool_counts,
            "period": {
                "first_query": metrics[0]["timestamp"] if metrics else None,
                "last_query": metrics[-1]["timestamp"] if metrics else None
            }
        }


class LangSmithTracer:
    """
    LangSmith integration for RAG tracing.

    Provides:
    - Query tracing
    - Tool execution tracking
    - Performance monitoring
    - Error tracking
    """

    def __init__(self):
        self.enabled = LANGSMITH_AVAILABLE and hasattr(settings, 'LANGSMITH_API_KEY')

        if self.enabled:
            try:
                self.client = LangSmithClient(
                    api_key=getattr(settings, 'LANGSMITH_API_KEY', None)
                )
                logger.info("LangSmith tracing enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client: {e}")
                self.enabled = False
        else:
            logger.info("LangSmith tracing disabled (not configured)")
            self.client = None

    @traceable(run_type="chain", name="hybrid_rag_query")
    async def trace_query(
        self,
        query: str,
        rag_tool,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Trace RAG query execution with LangSmith.

        Args:
            query: User query
            rag_tool: HybridRAGTool instance
            **kwargs: Additional arguments for RAG tool

        Returns:
            RAG result with tracing
        """
        start_time = time.time()

        try:
            result = await rag_tool.run(query=query, **kwargs)

            execution_time = time.time() - start_time

            # Record metrics
            PerformanceMetrics.record_query(
                query=query,
                execution_time=execution_time,
                intent_type=result.get("metadata", {}).get("intent_type", "unknown"),
                tools_executed=result.get("metadata", {}).get("tools_executed", []),
                result_count=len(result.get("sources", [])),
                success=result.get("success", False),
                metadata=result.get("metadata", {})
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            # Record failed query
            PerformanceMetrics.record_query(
                query=query,
                execution_time=execution_time,
                intent_type="error",
                tools_executed=[],
                result_count=0,
                success=False,
                metadata={"error": str(e)}
            )

            raise

    @traceable(run_type="tool", name="intent_classification")
    async def trace_intent_classification(
        self,
        classifier,
        query: str,
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Trace intent classification.

        Args:
            classifier: IntentClassifier instance
            query: User query
            conversation_history: Conversation context

        Returns:
            Classification result
        """
        return await classifier.classify(query, conversation_history)

    @traceable(run_type="retriever", name="vector_search")
    async def trace_vector_search(
        self,
        search_tool,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Trace vector search execution.

        Args:
            search_tool: VectorSearchTool instance
            query: Search query
            **kwargs: Search parameters

        Returns:
            Search results
        """
        return await search_tool.search_all(query=query, **kwargs)


def monitoring_decorator(func):
    """
    Decorator to add monitoring to any async function.

    Usage:
        @monitoring_decorator
        async def my_function(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        error = None

        try:
            result = await func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error = str(e)
            logger.error(f"Error in {func.__name__}: {e}")
            raise
        finally:
            execution_time = time.time() - start_time
            logger.info(
                f"{func.__name__} completed in {execution_time:.2f}s "
                f"(success={success})"
            )

            if error:
                logger.error(f"{func.__name__} failed: {error}")

    return wrapper


# Global instances
guardrails = Guardrails()
performance_metrics = PerformanceMetrics()
langsmith_tracer = LangSmithTracer()

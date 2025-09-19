"""StateAdapter - bridges dict-based lightweight state and full EchoChamberAnalystState API.

This allows incremental migration while nodes / monitoring still expect attribute
and method access (add_error, update_metrics, get_content_summary, etc.).
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from .state import TaskStatus, ProcessingMetrics

class StateAdapter:
    """Wrap a dict state to provide attribute + dict-style compatibility.

    This lets legacy code that expects an EchoChamberAnalystState (attribute / method
    access) coexist with newer dict-style node implementations while we converge
    on a single representation.
    """
    __slots__ = ["_data"]

    def __init__(self, data: Dict[str, Any]):
        # Use direct __setattr__ bypass to avoid recursion
        super().__setattr__("_data", data)
        # Ensure required structures exist
        self._data.setdefault("metrics", ProcessingMetrics())
        self._data.setdefault("audit_trail", [])
        self._data.setdefault("raw_content", [])
        self._data.setdefault("cleaned_content", [])
        self._data.setdefault("processed_content", [])
        self._data.setdefault("insights", [])
        self._data.setdefault("influencers", [])
        self._data.setdefault("conversation_history", [])
        self._data.setdefault("rag_context", {})

    # Attribute proxy -------------------------------------------------
    def __getattr__(self, item):
        if item in self._data:
            return self._data[item]
        raise AttributeError(item)

    def __setattr__(self, key, value):
        if key == "_data":
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    # Mapping protocol ------------------------------------------------
    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    def update(self, *args, **kwargs):
        return self._data.update(*args, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return self._data

    # Methods expected by existing nodes/monitoring ------------------
    def add_error(self, error: str, node: Optional[str] = None) -> None:
        metrics = getattr(self, "metrics", None)
        if hasattr(metrics, "errors"):
            metrics.errors.append(error)
        self._data["last_error"] = error
        self._data.setdefault("audit_trail", []).append({
            "timestamp": datetime.now().isoformat(),
            "action": "error_occurred",
            "error": error,
            "node": node or self._data.get("current_node"),
            "retry_count": self._data.get("retry_count", 0)
        })

    def update_metrics(self, tokens: int = 0, cost: float = 0.0, api_calls: int = 0):
        metrics = getattr(self, "metrics", None)
        if not metrics:
            return
        if hasattr(metrics, "total_tokens_used"):
            metrics.total_tokens_used += tokens
        if hasattr(metrics, "total_cost"):
            metrics.total_cost += cost
        if hasattr(metrics, "api_calls"):
            metrics.api_calls += api_calls

    def get_content_summary(self) -> Dict[str, int]:
        return {
            "raw_content": len(self._data.get("raw_content", [])),
            "cleaned_content": len(self._data.get("cleaned_content", [])),
            "processed_content": len(self._data.get("processed_content", [])),
            "total_insights": len(self._data.get("insights", [])),
            "identified_influencers": len(self._data.get("influencers", []))
        }

    # Convenience
    @property
    def workflow_id(self) -> str:
        return self._data.get("workflow_id", "unknown_workflow")

    @property
    def task_status(self):
        return self._data.get("task_status", TaskStatus.PENDING)

    @task_status.setter
    def task_status(self, value):
        self._data["task_status"] = value

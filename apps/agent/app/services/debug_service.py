"""In-process debug snapshot store for Flow traces.

The debug service records compact node input/output summaries keyed by
`trace_id`.  It is intentionally memory-backed for local development and tests;
production persistence can be added behind the same interface later.
"""

from __future__ import annotations


from datetime import datetime
from typing import Any


class DebugService:
    """Collect and expose summarized Flow node snapshots."""

    def __init__(self) -> None:
        """Initialize an empty trace-id to snapshots map."""
        self._snapshots_by_trace: dict[str, list[dict[str, Any]]] = {}

    async def save_node_snapshot(
        self,
        *,
        trace_id: str,
        request_id: str,
        session_id: str,
        turn_id: int,
        node_name: str,
        status: str,
        started_at: Any,
        finished_at: Any,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Append one node snapshot to the current trace."""
        snapshot = {
            "trace_id": trace_id,
            "request_id": request_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "node_name": node_name,
            "status": status,
            "started_at": self._normalize_time(started_at),
            "finished_at": self._normalize_time(finished_at),
            "input_summary": input_summary,
            "output_summary": output_summary,
            "error_code": error_code,
            "error_message": error_message,
        }
        self._snapshots_by_trace.setdefault(trace_id, []).append(snapshot)

    def list_trace_snapshots(self, trace_id: str) -> list[dict[str, Any]]:
        """Return snapshots for a trace without exposing internal list state."""
        return list(self._snapshots_by_trace.get(trace_id, []))

    def build_trace_payload(self, state: Any) -> dict[str, Any]:
        """Build a debug payload from a completed `FlowState`-like object."""
        return {
            "request_id": getattr(state, "request_id", ""),
            "trace_id": getattr(state, "trace_id", ""),
            "node_trace": list(getattr(state, "node_trace", [])),
            "final_status": getattr(state, "final_status", ""),
            "snapshots": self.list_trace_snapshots(getattr(state, "trace_id", "")),
        }

    @staticmethod
    def summarize_state_for_node_input(state: Any, node_name: str) -> dict[str, Any]:
        """Return the small input summary saved before/after a node run."""
        return {
            "node_name": node_name,
            "intent": getattr(state, "intent", None),
            "answer_type": getattr(state, "answer_type", None),
            "input_type": getattr(state, "input_type", None),
            "retry_count": getattr(state, "retry_count", 0),
        }

    @staticmethod
    def summarize_state_for_node_output(state: Any, node_name: str) -> dict[str, Any]:
        """Return the small output summary saved after a node run."""
        return {
            "node_name": node_name,
            "final_status": getattr(state, "final_status", None),
            "query_type": getattr(getattr(state, "query_plan", None), "query_type", None),
            "answer_type": getattr(state, "answer_type", None),
        }

    @staticmethod
    def _normalize_time(value: Any) -> str:
        """Serialize datetimes consistently in debug snapshots."""
        if isinstance(value, datetime):
            return value.isoformat(timespec="seconds")
        return str(value)

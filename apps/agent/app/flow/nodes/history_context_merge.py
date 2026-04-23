"""Restricted Flow node implementation for history context merge."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.context_service import ContextService


class HistoryContextMergeNode(BaseNode):
    """Flow node for the history context merge stage."""
    def __init__(self, service: ContextService):
        """Initialize the history context merge node."""
        super().__init__("history_context_merge", ("continue",), ("merged_slots", "context_used"))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        recent_context = await self.service.load_recent_context(state.session_id)
        merged_slots, merge_context_used = self.service.merge_slots(
            raw_slots=state.raw_slots,
            recent_context=recent_context,
            intent=state.intent or "",
            boundary_context=state.boundary_context,
        )
        context_used = dict(state.context_used)
        context_used.update({key: value for key, value in merge_context_used.items() if value not in (None, [], {})})
        patch = {"merged_slots": merged_slots, "context_used": context_used}
        return self.ensure_result(NodeResult(next_action="continue", state_patch=patch))

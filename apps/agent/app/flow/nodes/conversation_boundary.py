"""Restricted Flow node for conversation boundary decisions."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.context_service import ContextService
from app.services.conversation_boundary_service import ConversationBoundaryService


class ConversationBoundaryNode(BaseNode):
    """Decide multi-turn inheritance before slot merging."""

    def __init__(self, service: ConversationBoundaryService, context_service: ContextService):
        """Initialize the conversation boundary node."""
        super().__init__(
            "conversation_boundary",
            ("continue", "clarify_end"),
            ("intent", "answer_type", "boundary_context", "context_used", "answer_bundle"),
        )
        self.service = service
        self.context_service = context_service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        recent_context = await self.context_service.load_recent_context(state.session_id)
        result = self.service.decide(
            raw_slots=state.raw_slots,
            intent=state.intent or "",
            recent_context=recent_context,
            turn_id=state.turn_id,
        )
        next_action = "clarify_end" if result["next_action"] in {"clarify_missing_context", "clarify_decayed_context"} else "continue"
        return self.ensure_result(NodeResult(next_action=next_action, state_patch=result.get("patch") or {}))


__all__ = ["ConversationBoundaryNode"]

"""Restricted Flow node implementation for intent slot extract."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.intent_slot_service import IntentSlotService


class IntentSlotExtractNode(BaseNode):
    """Flow node for the intent slot extract stage."""
    def __init__(self, service: IntentSlotService):
        """Initialize the intent slot extract node."""
        super().__init__("intent_slot_extract", ("continue",), ("intent", "answer_type", "raw_slots"))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        parse_result = await self.service.parse(state.user_input, state.session_id)
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"intent": parse_result.intent, "answer_type": parse_result.answer_type, "raw_slots": parse_result.slots}))

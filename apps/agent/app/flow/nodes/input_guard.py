"""Restricted Flow node implementation for input guard."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.input_guard_service import InputGuardService


class InputGuardNode(BaseNode):
    """Flow node for the input guard stage."""
    def __init__(self, service: InputGuardService):
        super().__init__(
            "input_guard",
            ("safe_end", "clarify_end", "boundary_end", "closing_end", "continue"),
            ("input_type", "intent", "answer_type", "guidance_reason", "answer_bundle", "conversation_closed"),
        )
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        result = self.service.classify(state.user_input)
        patch: dict = {"input_type": result.input_type}
        if not result.allow_business_flow:
            if result.intent:
                patch["intent"] = result.intent
            patch["answer_type"] = result.suggested_answer_type
            patch["answer_bundle"] = {"final_answer": result.suggested_answer}
            if result.guidance_reason:
                patch["guidance_reason"] = result.guidance_reason
            if result.terminal_action == "closing_end":
                patch["conversation_closed"] = True
            return self.ensure_result(NodeResult(next_action=result.terminal_action, state_patch=patch))
        return self.ensure_result(NodeResult(next_action="continue", state_patch=patch))

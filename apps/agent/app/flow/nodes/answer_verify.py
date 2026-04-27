"""Restricted Flow node implementation for answer verify."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.answer_verify_service import AnswerVerifyService


class AnswerVerifyNode(BaseNode):
    """Flow node for the answer verify stage."""
    def __init__(self, service: AnswerVerifyService):
        """Initialize the answer verify node."""
        super().__init__("answer_verify", ("verified_end", "fallback"), ("answer_type", "answer_bundle"))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        result = self.service.verify(
            answer_type=state.answer_type or "",
            answer_bundle=state.answer_bundle,
            guidance_reason=str(state.guidance_reason or ""),
        )
        if result["failed"]:
            return self.ensure_result(NodeResult(next_action="fallback", state_patch={"answer_type": "fallback_answer", "answer_bundle": {"final_answer": result["fallback_answer"]}}))
        return self.ensure_result(NodeResult(next_action="verified_end"))

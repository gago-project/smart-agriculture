"""Restricted Flow node implementation for advice compose."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.advice_service import AdviceService


class AdviceComposeNode(BaseNode):
    """Flow node for the advice compose stage."""
    def __init__(self, service: AdviceService):
        """Initialize the advice compose node."""
        super().__init__("advice_compose", ("continue",), ("advice_result",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        advice_result = await self.service.compose(
            intent=state.intent or "",
            query_result=state.query_result,
            rule_result=state.rule_result,
            slots=state.merged_slots,
        )
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"advice_result": advice_result}))

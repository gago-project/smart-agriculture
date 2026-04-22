"""Restricted Flow node implementation for template render."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.template_service import TemplateService


class TemplateRenderNode(BaseNode):
    """Flow node for the template render stage."""
    def __init__(self, service: TemplateService):
        """Initialize the template render node."""
        super().__init__("template_render", ("go_advice", "go_response"), ("template_result",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        result = self.service.render(answer_type=state.answer_type or "", query_result=state.query_result, rule_result=state.rule_result, slots=state.merged_slots)
        return self.ensure_result(NodeResult(next_action=result["route_action"], state_patch={"template_result": result}))

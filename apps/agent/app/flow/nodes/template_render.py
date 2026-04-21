from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.template_service import TemplateService


class TemplateRenderNode(BaseNode):
    def __init__(self, service: TemplateService):
        super().__init__("template_render", ("go_advice", "go_response"), ("template_result",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        result = self.service.render(answer_type=state.answer_type or "", query_result=state.query_result, rule_result=state.rule_result, slots=state.merged_slots)
        return self.ensure_result(NodeResult(next_action=result["route_action"], state_patch={"template_result": result}))

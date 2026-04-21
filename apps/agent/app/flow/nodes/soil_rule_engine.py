from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.rule_engine_service import SoilRuleEngineService


class SoilRuleEngineNode(BaseNode):
    def __init__(self, service: SoilRuleEngineService):
        super().__init__("soil_rule_engine", ("template_only", "advice_only", "template_and_advice", "response_only"), ("rule_result",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        result = await self.service.evaluate(
            intent=state.intent or "",
            query_result=state.query_result,
            answer_type=state.answer_type or "",
            slots=state.merged_slots,
        )
        return self.ensure_result(NodeResult(next_action=result["route_action"], state_patch={"rule_result": result}))

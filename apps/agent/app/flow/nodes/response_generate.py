from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.response_service import ResponseService


class ResponseGenerateNode(BaseNode):
    def __init__(self, service: ResponseService):
        super().__init__("response_generate", ("continue",), ("answer_bundle",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        answer_bundle = await self.service.generate(
            intent=state.intent or "",
            answer_type=state.answer_type or "",
            query_result=state.query_result,
            rule_result=state.rule_result,
            template_result=state.template_result,
            advice_result=state.advice_result,
            slots=state.merged_slots,
            business_time=state.business_time,
        )
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"answer_bundle": answer_bundle}))

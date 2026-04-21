from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.fact_check_service import FactCheckService


class DataFactCheckNode(BaseNode):
    def __init__(self, service: FactCheckService):
        super().__init__("data_fact_check", ("retry_response", "go_verify", "fallback"), ("retry_count", "answer_type", "answer_bundle"))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        result = self.service.verify(answer_type=state.answer_type or "", answer_bundle=state.answer_bundle, query_result=state.query_result, rule_result=state.rule_result, template_result=state.template_result)
        if result["need_retry"]:
            if state.retry_count >= 2:
                return self.ensure_result(NodeResult(next_action="fallback", state_patch={"answer_type": "fallback_answer", "answer_bundle": {"final_answer": "当前回答多次校验未通过，已降级为安全兜底，请换一种问法重试。"}}))
            return self.ensure_result(NodeResult(next_action="retry_response", state_patch={"retry_count": state.retry_count + 1}))
        if result["failed"]:
            return self.ensure_result(NodeResult(next_action="fallback", state_patch={"answer_type": "fallback_answer", "answer_bundle": {"final_answer": result["fallback_answer"]}}))
        return self.ensure_result(NodeResult(next_action="go_verify"))

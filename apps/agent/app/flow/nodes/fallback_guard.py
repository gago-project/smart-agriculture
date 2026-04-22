"""Restricted Flow node implementation for fallback guard."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.response_service import ResponseService


class FallbackGuardNode(BaseNode):
    """Flow node for the fallback guard stage."""
    def __init__(self, response_service: ResponseService | None = None):
        """Initialize the fallback guard node."""
        super().__init__("fallback_guard", ("fallback_end",), ("answer_type", "answer_bundle"))
        self.response_service = response_service or ResponseService(qwen_client=None)

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        existing = str(state.answer_bundle.get("final_answer") or "").strip()
        if existing:
            safe_answer = existing
        elif state.errors:
            safe_answer = self.response_service.build_deterministic_answer(
                intent=state.intent or "",
                answer_type=state.answer_type or "",
                query_result=state.query_result,
                rule_result=state.rule_result,
                template_result=state.template_result,
                advice_result=state.advice_result,
                slots=state.merged_slots,
                business_time=state.business_time,
            ) or "当前请求处理过程中出现异常，已切换到安全兜底，请缩小范围后重试。"
        else:
            safe_answer = "当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。"
        return self.ensure_result(
            NodeResult(
                next_action="fallback_end",
                state_patch={"answer_type": state.answer_type or "fallback_answer", "answer_bundle": {"final_answer": safe_answer}},
            )
        )

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult


class FallbackGuardNode(BaseNode):
    def __init__(self):
        super().__init__("fallback_guard", ("fallback_end",), ("answer_type", "answer_bundle"))

    async def run(self, state: FlowState) -> NodeResult:
        existing = str(state.answer_bundle.get("final_answer") or "").strip()
        if existing:
            safe_answer = existing
        elif state.errors:
            safe_answer = "当前请求处理过程中出现异常，已切换到安全兜底，请缩小范围后重试。"
        else:
            safe_answer = "当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。"
        return self.ensure_result(
            NodeResult(
                next_action="fallback_end",
                state_patch={"answer_type": state.answer_type or "fallback_answer", "answer_bundle": {"final_answer": safe_answer}},
            )
        )

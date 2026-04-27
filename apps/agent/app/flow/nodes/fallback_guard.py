"""Restricted Flow node implementation for fallback guard."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult


class FallbackGuardNode(BaseNode):
    """Flow node for the fallback guard stage."""
    def __init__(self) -> None:
        super().__init__("fallback_guard", ("fallback_end",), ("answer_type", "answer_bundle"))

    async def run(self, state: FlowState) -> NodeResult:
        existing = str(state.answer_bundle.get("final_answer") or "").strip()
        if existing:
            safe_answer = existing
        elif state.query_result.records:
            # Use first available record to anchor the fallback answer
            first = state.query_result.records[0]
            sn = first.get("sn", "")
            county = first.get("county", "") or first.get("city", "")
            context = " ".join(filter(None, [county, sn]))
            safe_answer = (
                f"基于已查询到的数据（{context}），当前处理中断，"
                "请重新提问或缩小查询范围。"
            )
        elif state.answer_facts:
            entity = (
                state.answer_facts.get("entity_name")
                or state.answer_facts.get("entity_type")
                or ""
            )
            safe_answer = (
                f"当前处理中断{'（' + entity + '）' if entity else ''}，"
                "请重新提问或缩小查询范围。"
            )
        else:
            safe_answer = "当前无法稳定回答这个问题，请补充地区、设备或时间范围后重试。"

        return self.ensure_result(NodeResult(
            next_action="fallback_end",
            state_patch={
                "answer_type": state.answer_type or "fallback_answer",
                "answer_bundle": {"final_answer": safe_answer},
            },
        ))

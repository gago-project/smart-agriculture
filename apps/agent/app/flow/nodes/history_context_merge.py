"""Restricted Flow node implementation for history context merge."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.context_service import ContextService


class HistoryContextMergeNode(BaseNode):
    """Flow node for the history context merge stage."""
    def __init__(self, service: ContextService):
        """Initialize the history context merge node."""
        super().__init__("history_context_merge", ("continue",), ("intent", "answer_type", "merged_slots", "context_used", "answer_bundle"))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        recent_context = await self.service.load_recent_context(state.session_id)
        merged_slots, context_used = self.service.merge_slots(raw_slots=state.raw_slots, recent_context=recent_context, intent=state.intent or "")
        patch = {"merged_slots": merged_slots, "context_used": context_used}
        if self.service.should_force_clarification(context_used):
            patch.update(
                {
                    "intent": "clarification_needed",
                    "answer_type": "clarification_answer",
                    "answer_bundle": {
                        "final_answer": "这个追问缺少可继承的地区或设备上下文。请补充地区、设备或时间范围，例如：如东县最近怎么样，或 SNS00204333 最近有没有异常。"
                    },
                }
            )
        elif self.service.should_force_device_detail(raw_slots=state.raw_slots, merged_slots=merged_slots, context_used=context_used):
            patch.update({"intent": "soil_device_query", "answer_type": "soil_detail_answer"})
        return self.ensure_result(NodeResult(next_action="continue", state_patch=patch))

"""Restricted Flow node implementation for execution gate."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.execution_gate_service import ExecutionGateService


class ExecutionGateNode(BaseNode):
    """Flow node for the execution gate stage."""
    def __init__(self, service: ExecutionGateService):
        """Initialize the execution gate node."""
        super().__init__(
            "execution_gate",
            ("clarify_end", "block_end", "continue"),
            ("execution_gate_result", "answer_type", "answer_bundle"),
        )
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        result = self.service.evaluate(intent=state.intent or "", slots=state.merged_slots, business_time=state.business_time)
        if result["must_clarify"]:
            return self.ensure_result(
                NodeResult(
                    next_action="clarify_end",
                    state_patch={
                        "execution_gate_result": result,
                        "answer_type": "clarification_answer",
                        "answer_bundle": {"final_answer": result["clarify_message"]},
                    },
                )
            )
        if result["blocked"]:
            return self.ensure_result(
                NodeResult(
                    next_action="block_end",
                    state_patch={
                        "execution_gate_result": result,
                        "answer_type": "clarification_answer",
                        "answer_bundle": {"final_answer": result["block_message"]},
                    },
                )
            )
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"execution_gate_result": result}))

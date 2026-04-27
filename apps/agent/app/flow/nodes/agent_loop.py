"""Flow node wrapping AgentLoopService."""
from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.repositories.soil_repository import SoilRepository
from app.schemas.state import FlowState, NodeResult
from app.services.agent_loop_service import AgentLoopService


class AgentLoopNode(BaseNode):
    """Run the LLM + function-calling loop and populate final answer."""

    def __init__(self, service: AgentLoopService, *, repository: SoilRepository) -> None:
        super().__init__(
            "agent_loop",
            ("continue", "fallback"),
            ("intent", "answer_type", "answer_bundle", "query_result",
             "query_log_entries", "conversation_closed"),
        )
        self.service = service
        self.repository = repository

    async def run(self, state: FlowState) -> NodeResult:
        latest_business_time = await self.repository.latest_business_time_async()
        result = await self.service.run(
            user_input=state.user_input,
            session_id=state.session_id,
            turn_id=state.turn_id,
            latest_business_time=latest_business_time,
        )
        records = []
        for tool_result in result.tool_results:
            records.extend(tool_result.get("records", []))

        patch = {
            "answer_bundle": {"final_answer": result.final_answer},
            "query_result": {"records": records},
        }
        if result.is_fallback:
            patch["answer_type"] = "fallback_answer"
            return self.ensure_result(NodeResult(next_action="fallback", state_patch=patch))
        return self.ensure_result(NodeResult(next_action="continue", state_patch=patch))

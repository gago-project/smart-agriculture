"""Top-level application service that assembles and runs the Soil Agent.

SoilAgentService is the only class the API layer should call for agent
behavior. It owns dependency wiring, flow construction, query-log
writeback, context persistence, and response serialization.
"""

from __future__ import annotations


import asyncio
import os
from typing import Any

from app.flow.nodes import (
    AgentLoopNode,
    AnswerVerifyNode,
    DataFactCheckNode,
    FallbackGuardNode,
    InputGuardNode,
)
from app.flow.orchestrator import SoilMoistureFlowOrchestrator
from app.llm.qwen_client import QwenClient
from app.repositories.query_log_repository import QueryLogRepository
from app.repositories.soil_repository import SoilRepository
from app.flow.state_builder import build_flow_state
from app.repositories.session_context_repository import SessionContextRepository
from app.services.agent_loop_service import AgentLoopService
from app.services.answer_verify_service import AnswerVerifyService
from app.services.debug_service import DebugService
from app.services.fact_check_service import FactCheckService
from app.services.input_guard_service import InputGuardService
from app.services.tool_executor_service import ToolExecutorService


class SoilAgentService:
    """Facade around the LLM + Function Calling Soil Moisture Agent Flow."""

    def __init__(
        self,
        repository: SoilRepository | None = None,
        context_store: SessionContextRepository | None = None,
        query_log_repository: QueryLogRepository | None = None,
        qwen_client: QwenClient | None = None,
        debug_service: DebugService | None = None,
    ):
        self.repository = repository or SoilRepository.from_env()
        self.context_store = context_store or SessionContextRepository()
        self.query_log_repository = query_log_repository or QueryLogRepository(self.repository)
        self.qwen_client = qwen_client or QwenClient(api_key=os.getenv("QWEN_API_KEY", ""))
        self.debug_service = debug_service or DebugService()

        self.tool_executor = ToolExecutorService(self.repository)
        self.agent_loop_service = AgentLoopService(
            qwen_client=self.qwen_client,
            tool_executor=self.tool_executor,
            history_store=self.context_store,
        )
        self.orchestrator = SoilMoistureFlowOrchestrator(
            debug_service=self.debug_service,
            nodes={
                "input_guard": InputGuardNode(InputGuardService()),
                "agent_loop": AgentLoopNode(self.agent_loop_service, repository=self.repository),
                "data_fact_check": DataFactCheckNode(FactCheckService()),
                "answer_verify": AnswerVerifyNode(AnswerVerifyService()),
                "fallback_guard": FallbackGuardNode(),
            },
        )

    def chat(
        self,
        user_input: str,
        *,
        session_id: str,
        turn_id: int,
        request_id: str | None = None,
        channel: str = "web",
        timezone: str = "Asia/Shanghai",
    ) -> dict[str, Any]:
        """Synchronous wrapper for tests or scripts that are not async-aware."""
        try:
            return asyncio.run(
                self.achat(
                    user_input,
                    session_id=session_id,
                    turn_id=turn_id,
                    request_id=request_id,
                    channel=channel,
                    timezone=timezone,
                )
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self.achat(
                        user_input,
                        session_id=session_id,
                        turn_id=turn_id,
                        request_id=request_id,
                        channel=channel,
                        timezone=timezone,
                    )
                )
            finally:
                loop.close()

    async def achat(
        self,
        user_input: str,
        *,
        session_id: str,
        turn_id: int,
        request_id: str | None = None,
        channel: str = "web",
        timezone: str = "Asia/Shanghai",
    ) -> dict[str, Any]:
        """Run one user turn through the Flow and serialize output."""
        state = build_flow_state(
            user_input=user_input,
            session_id=session_id,
            turn_id=turn_id,
            request_id=request_id,
            channel=channel,
            timezone=timezone,
        )
        final_state = await self.orchestrator.run(state)
        self._enrich_query_log_entries(final_state)
        try:
            await self.query_log_repository.insert_many(final_state.query_log_entries)
        except Exception as exc:
            final_state.errors.append({"stage": "query_log_write", "error": str(exc)})
        await self.save_context_if_business_success(final_state)
        if final_state.conversation_closed:
            await self.context_store.clear_context(session_id)
        return {
            "session_id": session_id,
            "turn_id": turn_id,
            "request_id": final_state.request_id,
            "trace_id": final_state.trace_id,
            "input_type": final_state.input_type,
            "intent": final_state.intent,
            "answer_type": final_state.answer_type,
            "output_mode": final_state.output_mode,
            "guidance_reason": final_state.guidance_reason,
            "fallback_reason": final_state.fallback_reason,
            "final_answer": final_state.answer_bundle.get("final_answer", ""),
            "should_query": bool(final_state.query_result.records),
            "conversation_closed": final_state.conversation_closed,
            "status": "ok",
            "query_result": self._dump_bundle(final_state.query_result),
            "tool_trace": final_state.tool_trace,
            "answer_facts": final_state.answer_facts,
            "node_trace": final_state.node_trace,
            "final_status": final_state.final_status,
        }

    async def save_context_if_business_success(self, final_state) -> None:
        """History is saved inside AgentLoopService; clear on conversation close."""
        if final_state.conversation_closed:
            await self.context_store.clear_context(final_state.session_id)

    def _dump_bundle(self, bundle) -> dict[str, Any]:
        """Convert a Pydantic bundle to a compact response dictionary."""
        payload = bundle.model_dump(exclude_none=True)
        if all(value in ({}, [], "", None) for value in payload.values()):
            return {}
        return payload

    def _enrich_query_log_entries(self, final_state) -> None:
        """Attach turn-level question/answer context to each SQL audit row."""
        final_answer = getattr(final_state.answer_bundle, "final_answer", "")
        for entry in final_state.query_log_entries:
            entry.update(
                {
                    "request_text": final_state.user_input,
                    "response_text": final_answer,
                    "input_type": self._enum_text(final_state.input_type),
                    "intent": self._enum_text(final_state.intent),
                    "answer_type": self._enum_text(final_state.answer_type),
                    "final_status": final_state.final_status,
                }
            )

    @staticmethod
    def _enum_text(value) -> str | None:
        """Return plain enum/string values for persistence and JSON APIs."""
        if value is None:
            return None
        return getattr(value, "value", str(value))

    def get_summary_payload(self) -> dict[str, Any]:
        """Return a lightweight dashboard summary for /api/agent/summary."""
        records = self.repository.filter_records()
        latest_time = self.repository.latest_business_time()
        devices = []
        risky = 0
        for record in records[:10]:
            enriched = {**record, **self.repository.evaluate_status(record)}
            if enriched["soil_status"] != "not_triggered":
                risky += 1
            devices.append(enriched)
        water_values = [float(r["water20cm"]) for r in records if r.get("water20cm") is not None]
        avg_water = round(sum(water_values) / len(water_values), 2) if water_values else None
        return {
            "latest_time": latest_time,
            "total_records": len(records),
            "risky_devices": risky,
            "avg_water20cm": avg_water,
            "devices": devices,
        }

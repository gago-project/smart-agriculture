from __future__ import annotations

"""Top-level application service that assembles and runs the Soil Agent.

`SoilAgentService` is the only class the API layer should call for agent
behavior.  It owns dependency wiring, restricted Flow construction, query-log
writeback, context persistence, and response serialization.  Login/admin APIs
belong to the Next app and intentionally do not live here.
"""

import asyncio
import os
from typing import Any

from app.flow.nodes import (
    AdviceComposeNode,
    AnswerVerifyNode,
    DataFactCheckNode,
    ExecutionGateNode,
    FallbackGuardNode,
    HistoryContextMergeNode,
    InputGuardNode,
    IntentSlotExtractNode,
    RegionResolveNode,
    ResponseGenerateNode,
    SoilDataQueryNode,
    SoilRuleEngineNode,
    TemplateRenderNode,
    TimeResolveNode,
)
from app.flow.orchestrator import SoilMoistureFlowOrchestrator
from app.llm.qwen_client import QwenClient
from app.repositories.query_log_repository import QueryLogRepository
from app.repositories.soil_repository import SoilRepository
from app.flow.state_builder import build_flow_state
from app.repositories.session_context_repository import SessionContextRepository
from app.services.advice_service import AdviceService
from app.services.answer_verify_service import AnswerVerifyService
from app.services.context_service import ContextService
from app.services.debug_service import DebugService
from app.services.execution_gate_service import ExecutionGateService
from app.services.fact_check_service import FactCheckService
from app.services.input_guard_service import InputGuardService
from app.services.intent_slot_service import IntentSlotService
from app.services.region_service import RegionResolveService
from app.services.response_service import ResponseService
from app.services.rule_engine_service import SoilRuleEngineService
from app.services.soil_query_service import SoilQueryService
from app.services.template_service import TemplateService
from app.services.time_service import TimeResolveService


class SoilAgentService:
    """Facade around the full plans-defined Soil Moisture Agent Flow."""

    def __init__(
        self,
        repository: SoilRepository | None = None,
        context_store: SessionContextRepository | None = None,
        query_log_repository: QueryLogRepository | None = None,
        qwen_client: QwenClient | None = None,
        debug_service: DebugService | None = None,
    ):
        """Wire repositories, optional LLM client, services, and Flow nodes.

        The node registration order mirrors the architecture documents.  Each
        node receives a small service object so business logic remains testable
        without booting FastAPI or Docker.
        """
        self.repository = repository or SoilRepository.from_env()
        self.context_store = context_store or SessionContextRepository()
        self.query_log_repository = query_log_repository or QueryLogRepository(self.repository)
        self.qwen_client = qwen_client or QwenClient(api_key=os.getenv("QWEN_API_KEY", ""))
        self.debug_service = debug_service or DebugService()

        self.context_service = ContextService(self.context_store)
        self.soil_query_service = SoilQueryService(self.repository)
        self.orchestrator = SoilMoistureFlowOrchestrator(
            debug_service=self.debug_service,
            nodes={
                # Input/intent/context resolution nodes prepare a constrained
                # request state before any SQL planning is allowed.
                "input_guard": InputGuardNode(InputGuardService()),
                "intent_slot_extract": IntentSlotExtractNode(IntentSlotService(self.repository, qwen_client=self.qwen_client)),
                "history_context_merge": HistoryContextMergeNode(self.context_service),
                "time_resolve": TimeResolveNode(TimeResolveService(self.repository), self.soil_query_service),
                "region_resolve": RegionResolveNode(RegionResolveService(self.repository)),
                # Gate/query/rule/template nodes are the data authority path.
                # If the gate blocks, later data nodes should never run.
                "execution_gate": ExecutionGateNode(ExecutionGateService()),
                "soil_data_query": SoilDataQueryNode(self.soil_query_service),
                "soil_rule_engine": SoilRuleEngineNode(SoilRuleEngineService()),
                "template_render": TemplateRenderNode(TemplateService(self.repository)),
                "advice_compose": AdviceComposeNode(AdviceService()),
                # Generation is followed by fact checking and final answer
                # verification so LLM wording cannot overwrite data facts.
                "response_generate": ResponseGenerateNode(ResponseService(qwen_client=self.qwen_client)),
                "data_fact_check": DataFactCheckNode(FactCheckService()),
                "answer_verify": AnswerVerifyNode(AnswerVerifyService()),
                "fallback_guard": FallbackGuardNode(),
            }
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
        """Synchronous wrapper for tests or scripts that are not async-aware.

        FastAPI calls `achat` directly.  This method exists for unittest and
        local utility usage where creating an event loop at the call site would
        add noise.
        """
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
        """Run one user turn through the restricted Flow and serialize output.

        The order after `orchestrator.run` matters:
        1. write query logs produced by data nodes;
        2. save business context only when the final answer is verified;
        3. return the full contract to Web/BFF/test callers.
        """
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
        await self.query_log_repository.insert_many(final_state.query_log_entries)
        await self.save_context_if_business_success(final_state)
        # `should_query` represents whether the request actually planned a data
        # query.  Guardrail responses and non-business inputs must report false.
        should_query = final_state.final_status in {"verified_end", "fallback_end"} and bool(final_state.query_plan.query_type)
        return {
            "session_id": session_id,
            "turn_id": turn_id,
            "request_id": final_state.request_id,
            "trace_id": final_state.trace_id,
            "input_type": final_state.input_type,
            "intent": final_state.intent,
            "answer_type": final_state.answer_type,
            "final_answer": final_state.answer_bundle.get("final_answer", ""),
            "should_query": should_query,
            "status": "ok",
            "merged_slots": final_state.merged_slots.model_dump(exclude_none=True),
            "context_used": final_state.context_used,
            "business_time": self._dump_bundle(final_state.business_time),
            "execution_gate_result": self._dump_bundle(final_state.execution_gate_result),
            "query_plan": self._dump_bundle(final_state.query_plan),
            "query_result": self._dump_bundle(final_state.query_result),
            "rule_result": self._dump_bundle(final_state.rule_result),
            "template_result": self._dump_bundle(final_state.template_result),
            "advice_result": self._dump_bundle(final_state.advice_result),
            "node_trace": final_state.node_trace,
            "final_status": final_state.final_status,
        }

    async def save_context_if_business_success(self, final_state) -> None:
        """Persist Redis conversation context only for verified business turns."""
        if not self.context_service.should_save_business_context(final_state):
            return
        turn_context = self.context_service.build_turn_context(
            intent=final_state.intent or "",
            merged_slots=final_state.merged_slots,
        )
        final_state.context_to_save = turn_context
        await self.context_store.save_turn_context(
            session_id=final_state.session_id,
            turn_id=final_state.turn_id,
            turn_context=turn_context,
        )

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
        """Return a lightweight dashboard summary for `/api/agent/summary`.

        This is intentionally read-only and repository-backed; it should never
        fabricate totals if MySQL is unavailable.
        """
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

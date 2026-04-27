"""Unit tests for SoilAgentService contract (new 5-node architecture)."""

from __future__ import annotations

import asyncio
import unittest

from app.schemas.state import AnswerBundle, FlowState
from app.services.agent_service import SoilAgentService


class StubQueryLogRepository:
    def __init__(self) -> None:
        self.batches: list[list[dict]] = []

    async def insert_many(self, entries: list[dict]) -> None:
        self.batches.append(entries)


class StubSessionContextRepository:
    def __init__(self) -> None:
        self.cleared: list[str] = []

    async def clear_context(self, session_id: str) -> None:
        self.cleared.append(session_id)

    async def load_message_history(self, session_id: str) -> list[dict]:
        return []

    async def save_message_turn(self, session_id: str, turn_id: int, **kwargs) -> None:
        pass


class StubOrchestrator:
    def __init__(self, final_state: FlowState) -> None:
        self.final_state = final_state

    async def run(self, state: FlowState) -> FlowState:
        return self.final_state


class AgentServiceContractTest(unittest.TestCase):
    def test_chat_flushes_query_logs_with_enriched_fields(self) -> None:
        """Query log entries are enriched with request/response text and enum values."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="最近墒情怎么样",
            intent="soil_recent_summary",
            answer_type="soil_summary_answer",
            answer_bundle=AnswerBundle(final_answer="整体偏干"),
            query_log_entries=[{"query_id": "q1"}],
            final_status="verified_end",
        )
        log_repository = StubQueryLogRepository()
        service = SoilAgentService(
            repository=None,
            context_store=StubSessionContextRepository(),
            query_log_repository=log_repository,
        )
        service.orchestrator = StubOrchestrator(final_state)

        result = asyncio.run(service.achat("最近墒情怎么样", session_id="s1", turn_id=1))

        self.assertEqual(result["final_answer"], "整体偏干")
        self.assertEqual(len(log_repository.batches), 1)
        log_entry = log_repository.batches[0][0]
        self.assertEqual(log_entry["query_id"], "q1")
        self.assertEqual(log_entry["request_text"], "最近墒情怎么样")
        self.assertEqual(log_entry["response_text"], "整体偏干")
        self.assertEqual(log_entry["intent"], "soil_recent_summary")
        self.assertEqual(log_entry["answer_type"], "soil_summary_answer")
        self.assertEqual(log_entry["final_status"], "verified_end")

    def test_conversation_closed_clears_context_store(self) -> None:
        """When conversation_closed=True, context_store.clear_context is called."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="谢谢",
            answer_type="guidance_answer",
            guidance_reason="closing",
            answer_bundle=AnswerBundle(final_answer="好的，再见"),
            query_log_entries=[],
            final_status="closing_end",
            conversation_closed=True,
        )
        context_repo = StubSessionContextRepository()
        service = SoilAgentService(
            repository=None,
            context_store=context_repo,
            query_log_repository=StubQueryLogRepository(),
        )
        service.orchestrator = StubOrchestrator(final_state)

        asyncio.run(service.achat("谢谢", session_id="s1", turn_id=1))

        self.assertIn("s1", context_repo.cleared)

    def test_non_closing_does_not_clear_context(self) -> None:
        """Non-closing turns must not trigger context clearing."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="你好",
            answer_type="guidance_answer",
            guidance_reason="safe_hint",
            answer_bundle=AnswerBundle(final_answer="你好"),
            query_log_entries=[],
            final_status="safe_end",
            conversation_closed=False,
        )
        context_repo = StubSessionContextRepository()
        service = SoilAgentService(
            repository=None,
            context_store=context_repo,
            query_log_repository=StubQueryLogRepository(),
        )
        service.orchestrator = StubOrchestrator(final_state)

        asyncio.run(service.achat("你好", session_id="s1", turn_id=1))

        self.assertEqual(context_repo.cleared, [])

    def test_response_includes_new_contract_fields(self) -> None:
        """Response dict exposes output_mode, guidance_reason, fallback_reason, tool_trace, answer_facts."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="最近墒情怎么样",
            intent="soil_recent_summary",
            answer_type="soil_summary_answer",
            output_mode="normal",
            answer_bundle=AnswerBundle(final_answer="ok"),
            tool_trace=[{"tool_name": "query_soil_summary", "result_summary": "total=50"}],
            answer_facts={"total_records": 50},
            query_log_entries=[],
            final_status="verified_end",
        )
        service = SoilAgentService(
            repository=None,
            context_store=StubSessionContextRepository(),
            query_log_repository=StubQueryLogRepository(),
        )
        service.orchestrator = StubOrchestrator(final_state)

        result = asyncio.run(service.achat("最近墒情怎么样", session_id="s1", turn_id=1))

        for field in ("output_mode", "guidance_reason", "fallback_reason", "tool_trace", "answer_facts"):
            self.assertIn(field, result, f"Missing field: {field}")
        self.assertEqual(result["tool_trace"], [{"tool_name": "query_soil_summary", "result_summary": "total=50"}])
        self.assertEqual(result["answer_facts"], {"total_records": 50})

    def test_should_query_uses_query_result_entries_not_only_records(self) -> None:
        """Business responses with structured query_result.entries must still be treated as queried."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="最近墒情怎么样",
            intent="soil_recent_summary",
            answer_type="soil_summary_answer",
            output_mode="normal",
            answer_bundle=AnswerBundle(final_answer="ok"),
            query_result={
                "entries": [
                    {
                        "tool_name": "query_soil_summary",
                        "tool_args": {},
                        "result": {"total_records": 12},
                    }
                ]
            },
            final_status="verified_end",
        )
        service = SoilAgentService(
            repository=None,
            context_store=StubSessionContextRepository(),
            query_log_repository=StubQueryLogRepository(),
        )
        service.orchestrator = StubOrchestrator(final_state)

        result = asyncio.run(service.achat("最近墒情怎么样", session_id="s1", turn_id=1))

        self.assertEqual(result["query_result"]["entries"][0]["tool_name"], "query_soil_summary")
        self.assertEqual(result["should_query"], True)

    def test_query_log_error_does_not_raise_to_caller(self) -> None:
        """A log write failure must be captured in state.errors, not propagated."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="查墒情",
            answer_bundle=AnswerBundle(final_answer="ok"),
            query_log_entries=[{"query_id": "q1"}],
            final_status="verified_end",
        )

        class FailingLogRepo:
            async def insert_many(self, _):
                raise RuntimeError("db down")

        service = SoilAgentService(
            repository=None,
            context_store=StubSessionContextRepository(),
            query_log_repository=FailingLogRepo(),
        )
        service.orchestrator = StubOrchestrator(final_state)

        # Must not raise
        result = asyncio.run(service.achat("查墒情", session_id="s1", turn_id=1))
        self.assertEqual(result["final_answer"], "ok")


if __name__ == "__main__":
    unittest.main()

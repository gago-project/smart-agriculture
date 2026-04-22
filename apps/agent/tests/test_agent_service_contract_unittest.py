"""Unit tests for agent service contract."""

from __future__ import annotations

import asyncio
import unittest

from app.schemas.state import AnswerBundle, FlowState
from app.services.agent_service import SoilAgentService


class StubQueryLogRepository:
    """Repository helper for stub query log."""
    def __init__(self) -> None:
        """Initialize the stub query log repository."""
        self.batches: list[list[dict]] = []

    async def insert_many(self, entries: list[dict]) -> None:
        """Handle insert many on the stub query log repository."""
        self.batches.append(entries)


class StubSessionContextRepository:
    """Repository helper for stub session context."""
    def __init__(self) -> None:
        """Initialize the stub session context repository."""
        self.saved: list[dict] = []

    async def save_turn_context(self, *, session_id: str, turn_id: int, turn_context: dict) -> None:
        """Save turn context."""
        self.saved.append(
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "turn_context": turn_context,
            }
        )

    async def load_recent_context(self, session_id: str) -> list[dict]:
        """Load recent context."""
        return []


class StubOrchestrator:
    """Test double for stub orchestrator."""
    def __init__(self, final_state: FlowState) -> None:
        """Initialize the stub orchestrator."""
        self.final_state = final_state

    async def run(self, state: FlowState) -> FlowState:
        """Handle run on the stub orchestrator."""
        return self.final_state


class AgentServiceContractTest(unittest.TestCase):
    """Test cases for agent service contract."""
    def test_chat_flushes_query_logs_and_saves_business_context(self) -> None:
        """Verify chat flushes query logs and saves business context."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="最近墒情怎么样",
            intent="soil_recent_summary",
            answer_type="soil_summary_answer",
            answer_bundle=AnswerBundle(final_answer="ok"),
            query_log_entries=[{"query_id": "q1"}],
            final_status="verified_end",
            merged_slots={"county_name": "如东县", "time_range": "last_7_days"},
        )
        context_repository = StubSessionContextRepository()
        log_repository = StubQueryLogRepository()
        service = SoilAgentService(
            repository=None,
            context_store=context_repository,
            query_log_repository=log_repository,
        )
        service.orchestrator = StubOrchestrator(final_state)

        result = asyncio.run(service.achat("最近墒情怎么样", session_id="s1", turn_id=1))

        self.assertEqual(result["final_answer"], "ok")
        self.assertEqual(len(log_repository.batches), 1)
        self.assertEqual(len(log_repository.batches[0]), 1)
        self.assertEqual(log_repository.batches[0][0]["query_id"], "q1")
        self.assertEqual(log_repository.batches[0][0]["request_text"], "最近墒情怎么样")
        self.assertEqual(log_repository.batches[0][0]["response_text"], "ok")
        self.assertEqual(log_repository.batches[0][0]["intent"], "soil_recent_summary")
        self.assertEqual(log_repository.batches[0][0]["answer_type"], "soil_summary_answer")
        self.assertEqual(log_repository.batches[0][0]["final_status"], "verified_end")
        self.assertEqual(len(context_repository.saved), 1)
        self.assertEqual(final_state.context_to_save["last_intent"], "soil_recent_summary")

    def test_non_business_result_does_not_save_context(self) -> None:
        """Verify non business result does not save context."""
        final_state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="hi",
            input_type="greeting",
            answer_type="safe_hint_answer",
            answer_bundle=AnswerBundle(final_answer="hello"),
            query_log_entries=[],
            final_status="safe_end",
        )
        context_repository = StubSessionContextRepository()
        log_repository = StubQueryLogRepository()
        service = SoilAgentService(
            repository=None,
            context_store=context_repository,
            query_log_repository=log_repository,
        )
        service.orchestrator = StubOrchestrator(final_state)

        asyncio.run(service.achat("hi", session_id="s1", turn_id=1))

        self.assertEqual(log_repository.batches, [[]])
        self.assertEqual(context_repository.saved, [])


if __name__ == "__main__":
    unittest.main()

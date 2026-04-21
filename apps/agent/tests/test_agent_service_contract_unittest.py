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
        self.saved: list[dict] = []

    async def save_turn_context(self, *, session_id: str, turn_id: int, turn_context: dict) -> None:
        self.saved.append(
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "turn_context": turn_context,
            }
        )

    async def load_recent_context(self, session_id: str) -> list[dict]:
        return []


class StubOrchestrator:
    def __init__(self, final_state: FlowState) -> None:
        self.final_state = final_state

    async def run(self, state: FlowState) -> FlowState:
        return self.final_state


class AgentServiceContractTest(unittest.TestCase):
    def test_chat_flushes_query_logs_and_saves_business_context(self) -> None:
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
        self.assertEqual(log_repository.batches, [[{"query_id": "q1"}]])
        self.assertEqual(len(context_repository.saved), 1)
        self.assertEqual(final_state.context_to_save["last_intent"], "soil_recent_summary")

    def test_non_business_result_does_not_save_context(self) -> None:
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

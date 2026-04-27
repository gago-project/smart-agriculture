"""Unit tests for agent service."""

import unittest

from app.services.agent_service import SoilAgentService
from support_repositories import SeedSoilRepository


class FailingQueryLogRepository:
    """Repository helper for failing query log."""
    async def insert_many(self, entries):
        """Handle insert many on the failing query log repository."""
        raise RuntimeError("query log write failed")


class AgentServiceTest(unittest.TestCase):
    """Test cases for agent service."""
    def setUp(self):
        """Prepare the shared fixtures for each test case."""
        self.service = SoilAgentService(repository=SeedSoilRepository())

    def test_meaningless_input_returns_safe_hint_without_query(self):
        """Verify meaningless input returns safe hint without query."""
        result = self.service.chat("h d k j h sa d k l j", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "safe_hint_answer")
        self.assertFalse(result["should_query"])
        self.assertIn("墒情", result["final_answer"])

    def test_summary_question_returns_soil_summary(self):
        """Verify summary question returns soil summary."""
        result = self.service.chat("最近墒情怎么样", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["intent"], "soil_recent_summary")
        self.assertIn("整体", result["final_answer"])

    def test_query_log_write_failure_does_not_break_answer(self):
        """Verify query log write failure does not break answer."""
        service = SoilAgentService(
            repository=SeedSoilRepository(),
            query_log_repository=FailingQueryLogRepository(),
        )

        result = service.chat("最近墒情怎么样", session_id="log-fail", turn_id=1)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertIn("墒情概况", result["final_answer"])

    def test_warning_question_uses_template_answer(self):
        """Verify warning question uses template answer."""
        result = self.service.chat("SNS00204333 需要发预警吗", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_warning_answer")
        self.assertEqual(result["intent"], "soil_warning_generation")
        self.assertIn("预警", result["final_answer"])


class AgentServiceNewFlowSmokeTest(unittest.TestCase):
    def setUp(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.llm.qwen_client import QwenClient

        qwen = MagicMock(spec=QwenClient)
        qwen.available.return_value = True
        qwen.call_with_tools = AsyncMock(return_value={
            "type": "text",
            "content": "全省整体墒情偏干，平均相对含水量 55%。",
        })
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=qwen,
        )

    def test_chat_returns_final_answer(self):
        result = self.service.chat("全省墒情怎么样", session_id="smoke1", turn_id=1)
        self.assertIn("final_answer", result)
        self.assertGreater(len(result["final_answer"]), 0)

    def test_new_flow_does_not_use_old_nodes(self):
        node_names = list(self.service.orchestrator.runner.nodes.keys())
        self.assertIn("agent_loop", node_names)
        self.assertNotIn("intent_slot_extract", node_names)
        self.assertNotIn("conversation_boundary", node_names)
        self.assertNotIn("history_context_merge", node_names)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for agent service."""

import unittest
from unittest.mock import AsyncMock, MagicMock

from app.llm.qwen_client import QwenClient
from app.services.agent_service import SoilAgentService
from tests.support_repositories import SeedSoilRepository


class AgentServiceInputGuardTest(unittest.TestCase):
    """InputGuard-level behavior: no LLM required."""

    def setUp(self):
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
        )

    def test_meaningless_input_returns_guidance_answer_with_safe_hint(self):
        result = self.service.chat("h d k j h sa d k l j", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "safe_hint")
        self.assertFalse(result["should_query"])
        self.assertIn("墒情", result["final_answer"])

    def test_closing_returns_guidance_answer_and_closes_conversation(self):
        result = self.service.chat("谢谢", session_id="close1", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "closing")
        self.assertTrue(result["conversation_closed"])

    def test_out_of_scope_returns_guidance_answer_boundary(self):
        result = self.service.chat("查一下明天天气", session_id="oos1", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "boundary")
        self.assertFalse(result["should_query"])

    def test_query_log_write_failure_does_not_break_answer(self):
        class FailingQueryLogRepository:
            async def insert_many(self, entries):
                raise RuntimeError("query log write failed")

        service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
            query_log_repository=FailingQueryLogRepository(),
        )
        result = service.chat("最近墒情怎么样", session_id="log-fail", turn_id=1)

        self.assertEqual(result["status"], "ok")
        self.assertIsInstance(result["final_answer"], str)
        self.assertGreater(len(result["final_answer"]), 0)


class AgentServiceNewFlowSmokeTest(unittest.TestCase):
    def setUp(self):
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

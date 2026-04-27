"""Unit tests for region handling in the new tool-executor architecture.

IntentSlotService was deleted. Region parameters are now passed directly by
the LLM to the tool executor. These tests verify that the tool executor
handles region filters correctly and that the InputGuard routes
out-of-scope requests to guidance_answer without a DB query.
"""

from __future__ import annotations

import asyncio
import unittest

from app.llm.qwen_client import QwenClient
from app.services.agent_service import SoilAgentService
from app.services.tool_executor_service import ToolExecutorService
from tests.support_repositories import SeedSoilRepository


class ToolExecutorRegionFilterTest(unittest.TestCase):
    """Tool executor returns correct structure for region-scoped queries."""

    def setUp(self) -> None:
        self.repo = SeedSoilRepository()
        self.executor = ToolExecutorService(repository=self.repo)

    def test_detail_query_with_city_filter_returns_entity_type_region(self):
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_detail",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "city": "南京市",
            },
        ))
        self.assertEqual(result["entity_type"], "region")
        self.assertIn("latest_record", result)
        self.assertIn("status_summary", result)

    def test_detail_query_with_sn_filter_returns_entity_type_device(self):
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_detail",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "sn": "SNS00204333",
            },
        ))
        self.assertEqual(result["entity_type"], "device")
        self.assertEqual(result["entity_name"], "SNS00204333")

    def test_summary_query_with_city_filter_returns_scoped_stats(self):
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_summary",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "city": "南京市",
            },
        ))
        self.assertIn("total_records", result)
        self.assertIn("avg_water20cm", result)

    def test_diagnose_region_exists_returns_entity_exists_flag(self):
        result = asyncio.run(self.executor.execute(
            tool_name="diagnose_empty_result",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "scenario": "region_exists",
                "city": "南京市",
            },
        ))
        self.assertIn("entity_exists", result)
        self.assertIn("diagnosis", result)
        self.assertIn(result["diagnosis"], ("data_exists", "entity_not_found"))

    def test_diagnose_unknown_region_returns_entity_not_found(self):
        result = asyncio.run(self.executor.execute(
            tool_name="diagnose_empty_result",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "scenario": "region_exists",
                "city": "不存在市XYZABC",
            },
        ))
        self.assertFalse(result["entity_exists"])
        self.assertEqual(result["diagnosis"], "entity_not_found")


class OutOfScopeRoutingTest(unittest.TestCase):
    """Out-of-scope inputs are routed to guidance_answer without a DB query."""

    def setUp(self) -> None:
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
        )

    def test_weather_question_routes_to_guidance_answer(self):
        result = self.service.chat("查一下明天天气", session_id="oos1", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "boundary")
        self.assertFalse(result["should_query"])

    def test_greeting_routes_to_guidance_answer(self):
        result = self.service.chat("你好", session_id="oos2", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertFalse(result["should_query"])

    def test_intent_slot_service_is_deleted(self):
        """IntentSlotService was removed; importing it must fail."""
        with self.assertRaises(ImportError):
            import app.services.intent_slot_service  # noqa: F401


if __name__ == "__main__":
    unittest.main()

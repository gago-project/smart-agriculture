"""Behavior contract tests for the new 5-node LLM + Function Calling architecture.

All tests run with api_key="" so no real LLM calls are made.
Business queries hit the agent loop which returns a fallback when no LLM key exists.
Non-business queries are intercepted by InputGuardNode before the agent loop.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.llm.qwen_client import QwenClient
from app.schemas.enums import AnswerType, GuidanceReason, FallbackReason
from app.services.agent_service import SoilAgentService
from app.services.agent_loop_service import AgentLoopService, AgentLoopResult
from app.services.parameter_resolver_service import ParameterResolverService
from tests.support_repositories import SeedSoilRepository

_VALID_ANSWER_TYPES = {v.value for v in AnswerType} | {None}


def _mock_agent_loop_service(
    tool_calls: list[dict],
    final_text: str,
    *,
    repository: SeedSoilRepository | None = None,
) -> AgentLoopService:
    """Return a mock AgentLoopService that calls tools then returns final_text."""
    from app.repositories.session_context_repository import SessionContextRepository
    from app.services.tool_executor_service import ToolExecutorService

    repo = repository or SeedSoilRepository()
    mock_qwen = MagicMock(spec=QwenClient)
    mock_qwen.available.return_value = True
    responses = [
        {"type": "tool_calls", "calls": tool_calls},
        {"type": "text", "content": final_text},
    ]
    mock_qwen.call_with_tools = AsyncMock(side_effect=responses)

    return AgentLoopService(
        qwen_client=mock_qwen,
        tool_executor=ToolExecutorService(repository=repo),
        history_store=SessionContextRepository(),
        resolver=ParameterResolverService(repo),
    )


class InputGuardBehaviorTest(unittest.TestCase):
    """InputGuard correctly classifies non-business inputs without LLM."""

    def setUp(self):
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
        )

    def test_closing_utterance_returns_guidance_answer_with_closing_reason(self):
        result = self.service.chat("谢谢", session_id="closing", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "closing")
        self.assertFalse(result["should_query"])
        self.assertTrue(result["conversation_closed"])

    def test_out_of_scope_returns_guidance_answer_with_boundary_reason(self):
        result = self.service.chat("查一下明天天气", session_id="bound", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "boundary")
        self.assertFalse(result["should_query"])

    def test_greeting_returns_guidance_answer_with_safe_hint_reason(self):
        result = self.service.chat("你好", session_id="greet", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "safe_hint")
        self.assertFalse(result["should_query"])

    def test_ambiguous_input_returns_guidance_answer_with_clarification_reason(self):
        result = self.service.chat("看看", session_id="ambig", turn_id=1)

        self.assertEqual(result["answer_type"], "guidance_answer")
        self.assertEqual(result["guidance_reason"], "clarification")
        self.assertFalse(result["should_query"])

    def test_closing_then_follow_up_has_no_prior_context(self):
        self.service.chat("如东县最近怎么样", session_id="ctx-close", turn_id=1)
        closing = self.service.chat("谢谢", session_id="ctx-close", turn_id=2)
        self.assertTrue(closing["conversation_closed"])


class P0RedLineTest(unittest.TestCase):
    """P0: business queries must hit a Tool before generating a business answer."""

    def setUp(self):
        self.repo = SeedSoilRepository()
        self.repo.extra_region_aliases = [
            {
                "alias_name": "南通市",
                "canonical_name": "南通市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "canonical",
            },
            {
                "alias_name": "如东县",
                "canonical_name": "如东县",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "canonical",
            },
        ]

    def test_business_query_without_llm_key_returns_fallback_answer(self):
        service = SoilAgentService(
            repository=self.repo,
            qwen_client=QwenClient(api_key=""),
        )
        result = service.chat("最近墒情怎么样", session_id="p0", turn_id=1)

        # Without LLM key the agent loop can't call tools, so falls back
        self.assertIsInstance(result["final_answer"], str)
        self.assertGreater(len(result["final_answer"]), 0)

    def test_business_answer_without_tool_call_is_intercepted_as_fallback(self):
        """If the mock LLM returns text directly (no tool call), P0 must intercept."""
        from app.repositories.session_context_repository import SessionContextRepository
        from app.services.tool_executor_service import ToolExecutorService

        mock_qwen = MagicMock(spec=QwenClient)
        mock_qwen.available.return_value = True
        # LLM returns text directly without calling any tool
        mock_qwen.call_with_tools = AsyncMock(return_value={
            "type": "text",
            "content": "最近墒情偏干，平均含水量约55%。",
        })

        svc = AgentLoopService(
            qwen_client=mock_qwen,
            tool_executor=ToolExecutorService(repository=self.repo),
            history_store=SessionContextRepository(),
        )
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="最近墒情怎么样",
            session_id="p0-intercept",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
            is_business_query=True,
        ))

        # P0 must intercept: is_fallback=True, fallback_reason=tool_missing
        self.assertTrue(result.is_fallback)
        self.assertEqual(result.fallback_reason, "tool_missing")
        self.assertEqual(len(result.tool_calls_made), 0)

    def test_non_business_bypass_does_not_trigger_p0(self):
        """Non-business queries may return text without tool calls (is_business_query=False)."""
        from app.repositories.session_context_repository import SessionContextRepository
        from app.services.tool_executor_service import ToolExecutorService

        mock_qwen = MagicMock(spec=QwenClient)
        mock_qwen.available.return_value = True
        mock_qwen.call_with_tools = AsyncMock(return_value={
            "type": "text",
            "content": "好的，我是墒情助手。",
        })

        svc = AgentLoopService(
            qwen_client=mock_qwen,
            tool_executor=ToolExecutorService(repository=self.repo),
            history_store=SessionContextRepository(),
        )
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="你好",
            session_id="p0-bypass",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
            is_business_query=False,  # P0 does NOT apply
        ))

        self.assertFalse(result.is_fallback)
        self.assertEqual(len(result.tool_calls_made), 0)


class AnswerTypeContractTest(unittest.TestCase):
    """answer_type is restricted to exactly 5 canonical values."""

    def setUp(self):
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
        )

    def test_answer_type_always_in_5_canonical_values(self):
        test_inputs = [
            "谢谢",
            "查一下明天天气",
            "最近墒情怎么样",
            "你好",
            "看看",
        ]
        for text in test_inputs:
            result = self.service.chat(text, session_id=text[:4], turn_id=1)
            self.assertIn(
                result["answer_type"], _VALID_ANSWER_TYPES,
                f"Unexpected answer_type={result['answer_type']!r} for input {text!r}",
            )

    def test_old_answer_type_names_never_returned(self):
        banned_types = {
            "clarification_answer", "closing_answer", "safe_hint_answer",
            "boundary_answer", "soil_anomaly_answer", "soil_warning_answer",
        }
        for text in ["谢谢", "查一下明天天气", "你好", "最近墒情怎么样"]:
            result = self.service.chat(text, session_id=text[:4] + "ban", turn_id=1)
            self.assertNotIn(result["answer_type"], banned_types,
                             f"Got banned answer_type {result['answer_type']!r} for {text!r}")


class StructuredEvidenceFieldsTest(unittest.TestCase):
    """Response must include structured evidence fields."""

    def setUp(self):
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
        )

    def test_response_includes_tool_trace_and_answer_facts(self):
        result = self.service.chat("最近墒情怎么样", session_id="evidence1", turn_id=1)

        self.assertIn("tool_trace", result)
        self.assertIn("answer_facts", result)
        self.assertIsInstance(result["tool_trace"], list)
        self.assertIsInstance(result["answer_facts"], dict)

    def test_response_includes_query_result(self):
        result = self.service.chat("最近墒情怎么样", session_id="evidence2", turn_id=1)

        self.assertIn("query_result", result)
        self.assertIsInstance(result["query_result"], dict)

    def test_guidance_answer_includes_guidance_reason_field(self):
        result = self.service.chat("谢谢", session_id="guidance-fields", turn_id=1)

        self.assertIn("guidance_reason", result)
        self.assertIn("fallback_reason", result)
        self.assertIn("output_mode", result)

    def test_fallback_answer_includes_fallback_reason_field(self):
        result = self.service.chat("最近墒情怎么样", session_id="fallback-fields", turn_id=1)

        # With no LLM key, business query → fallback
        self.assertIn("fallback_reason", result)
        self.assertIn("guidance_reason", result)
        self.assertIn("output_mode", result)


class ToolToAnswerTypeMappingTest(unittest.TestCase):
    """summary/ranking/detail tools map to the correct answer_type."""

    _DATA_START = "2026-04-01 00:00:00"
    _DATA_END = "2026-04-30 23:59:59"

    def setUp(self):
        self.repo = SeedSoilRepository()
        self.repo.extra_region_aliases = [
            {
                "alias_name": "南通市",
                "canonical_name": "南通市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "canonical",
            },
            {
                "alias_name": "如东县",
                "canonical_name": "如东县",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "canonical",
            },
        ]

    def _run_with_tool(self, tool_name: str, tool_args: dict, final_text: str) -> dict:
        svc = SoilAgentService(
            repository=self.repo,
            qwen_client=QwenClient(api_key=""),
        )
        mock_loop = _mock_agent_loop_service(
            tool_calls=[{"tool_name": tool_name, "tool_args": tool_args, "call_id": "c1"}],
            final_text=final_text,
            repository=self.repo,
        )
        svc.agent_loop_service = mock_loop
        # The runner holds the live nodes dict
        from app.flow.nodes import AgentLoopNode
        svc.orchestrator.runner.nodes["agent_loop"] = AgentLoopNode(mock_loop, repository=self.repo)
        return svc.chat("测试", session_id="map-test", turn_id=1)

    def test_query_soil_summary_produces_soil_summary_answer(self):
        result = self._run_with_tool(
            "query_soil_summary",
            {"start_time": self._DATA_START, "end_time": self._DATA_END},
            "整体墒情偏干。",
        )
        self.assertEqual(result["answer_type"], "soil_summary_answer")

    def test_query_soil_ranking_produces_soil_ranking_answer(self):
        result = self._run_with_tool(
            "query_soil_ranking",
            {"start_time": self._DATA_START, "end_time": self._DATA_END, "aggregation": "county"},
            "如东县最严重。",
        )
        self.assertEqual(result["answer_type"], "soil_ranking_answer")

    def test_query_soil_detail_produces_soil_detail_answer(self):
        result = self._run_with_tool(
            "query_soil_detail",
            {"start_time": self._DATA_START, "end_time": self._DATA_END, "county": "如东县"},
            "如东县最新含水量 55%。",
        )
        self.assertEqual(result["answer_type"], "soil_detail_answer")

    def test_diagnose_empty_result_produces_fallback_answer(self):
        result = self._run_with_tool(
            "diagnose_empty_result",
            {"start_time": "2025-04-14 00:00:00", "end_time": "2025-04-20 23:59:59", "scenario": "region_exists", "city": "延安市"},
            "该地区暂无数据。",
        )
        # diagnose → fallback_answer
        self.assertEqual(result["answer_type"], "fallback_answer")


if __name__ == "__main__":
    unittest.main()

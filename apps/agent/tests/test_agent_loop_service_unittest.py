import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from tests.support_repositories import SeedSoilRepository
from app.llm.qwen_client import QwenClient
from app.repositories.session_context_repository import SessionContextRepository
from app.services.parameter_resolver_service import ResolvedParams
from app.services.tool_executor_service import ToolExecutorService
from app.services.agent_loop_service import AgentLoopService, AgentLoopResult


def _mock_qwen(responses: list[dict]) -> QwenClient:
    client = MagicMock(spec=QwenClient)
    client.available.return_value = True
    normalized_responses: list[dict] = []
    for response in responses:
        if response.get("type") == "tool_call":
            normalized_responses.append(
                {
                    "type": "tool_calls",
                    "calls": [
                        {
                            "tool_name": response["tool_name"],
                            "tool_args": response["tool_args"],
                            "call_id": response.get("call_id", ""),
                        }
                    ],
                }
            )
        else:
            normalized_responses.append(response)
    client.call_with_tools = AsyncMock(side_effect=normalized_responses)
    return client


class AgentLoopServiceTest(unittest.TestCase):
    def setUp(self):
        self.repo = SeedSoilRepository()
        self.history_store = SessionContextRepository()
        self.executor = ToolExecutorService(repository=self.repo)

    def _make_service(self, qwen_responses: list[dict]) -> AgentLoopService:
        return AgentLoopService(
            qwen_client=_mock_qwen(qwen_responses),
            tool_executor=self.executor,
            history_store=self.history_store,
        )

    def test_single_tool_call_then_text_returns_final_answer(self):
        svc = self._make_service([
            {"type": "tool_call", "tool_name": "query_soil_summary",
             "tool_args": {"start_time": "2025-04-14 00:00:00", "end_time": "2025-04-20 23:59:59"},
             "call_id": "c1"},
            {"type": "text", "content": "延安市整体墒情偏干，平均含水量 55%。"},
        ])
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="查延安市最近7天墒情",
            session_id="test1",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))
        self.assertIsInstance(result.final_answer, str)
        self.assertIn("55", result.final_answer)
        self.assertEqual(len(result.tool_calls_made), 1)
        self.assertEqual(result.tool_calls_made[0]["tool_name"], "query_soil_summary")

    def test_no_llm_key_returns_fallback_message(self):
        svc = AgentLoopService(
            qwen_client=QwenClient(api_key=""),
            tool_executor=self.executor,
            history_store=self.history_store,
        )
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="查墒情",
            session_id="test2",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))
        self.assertIsInstance(result.final_answer, str)
        self.assertTrue(result.is_fallback)

    def test_max_iterations_guard_stops_runaway_loop(self):
        infinite_calls = [
            {"type": "tool_call", "tool_name": "query_soil_summary",
             "tool_args": {"start_time": "2025-04-14 00:00:00", "end_time": "2025-04-20 23:59:59"},
             "call_id": f"c{i}"}
            for i in range(20)
        ]
        svc = self._make_service(infinite_calls)
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="查墒情",
            session_id="test3",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))
        self.assertLessEqual(len(result.tool_calls_made), 5)
        self.assertIsInstance(result.final_answer, str)

    def test_tool_validation_error_is_included_in_messages_to_llm(self):
        svc = self._make_service([
            {"type": "tool_call", "tool_name": "query_soil_ranking",
             "tool_args": {"start_time": "2025-04-14 00:00:00", "end_time": "2025-04-20 23:59:59",
                           "aggregation": "county", "top_n": 100},
             "call_id": "c1"},
            {"type": "text", "content": "top_n 超过上限，已为你展示前20名。"},
        ])
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="查前100名",
            session_id="test4",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))
        self.assertIsInstance(result.final_answer, str)
        self.assertGreater(len(result.messages), 2)

    def test_history_is_loaded_into_messages(self):
        asyncio.run(self.history_store.save_message_turn(
            "s_history", 1,
            user_message="查延安市",
            assistant_message="延安市偏干",
            tool_calls=[], tool_results=[],
        ))
        svc = self._make_service([
            {"type": "text", "content": "志丹县最严重。"},
        ])
        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="那最严重的县呢",
            session_id="s_history",
            turn_id=2,
            latest_business_time="2025-04-20 08:00:00",
        ))
        user_msgs = [m for m in result.messages if m["role"] == "user"]
        self.assertGreaterEqual(len(user_msgs), 2)

    def test_completed_turn_persists_standard_tool_transcript(self):
        svc = self._make_service([
            {
                "type": "tool_call",
                "tool_name": "query_soil_summary",
                "tool_args": {"start_time": "2025-04-14 00:00:00", "end_time": "2025-04-20 23:59:59"},
                "call_id": "call_1",
            },
            {"type": "text", "content": "延安市最近7天整体偏干。"},
        ])

        asyncio.run(svc.run(
            user_input="查延安市最近7天墒情",
            session_id="persist_history",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))

        history = asyncio.run(self.history_store.load_history("persist_history"))
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["tool_calls"][0]["type"], "function")
        self.assertEqual(history[1]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(history[1]["tool_calls"][0]["function"]["name"], "query_soil_summary")
        self.assertEqual(history[2]["role"], "tool")
        self.assertEqual(history[2]["tool_call_id"], "call_1")
        self.assertEqual(history[3]["role"], "assistant")
        self.assertEqual(history[3]["content"], "延安市最近7天整体偏干。")

    def test_history_persists_resolved_tool_args_instead_of_raw_args(self):
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=ResolvedParams(
            tool_name="query_soil_summary",
            raw_args={
                "city": "南通",
                "start_time": "2025-04-14 00:00:00",
                "end_time": "2025-04-20 23:59:59",
            },
            resolved_args={
                "city": "南通市",
                "start_time": "2025-04-14 00:00:00",
                "end_time": "2025-04-20 23:59:59",
            },
        ))
        svc = AgentLoopService(
            qwen_client=_mock_qwen([
                {
                    "type": "tool_call",
                    "tool_name": "query_soil_summary",
                    "tool_args": {
                        "city": "南通",
                        "start_time": "2025-04-14 00:00:00",
                        "end_time": "2025-04-20 23:59:59",
                    },
                    "call_id": "call_resolved",
                },
                {"type": "text", "content": "南通市最近7天整体偏干。"},
            ]),
            tool_executor=self.executor,
            history_store=self.history_store,
            resolver=resolver,
        )

        asyncio.run(svc.run(
            user_input="查南通最近7天墒情",
            session_id="persist_resolved_history",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))

        history = asyncio.run(self.history_store.load_history("persist_resolved_history"))
        stored_args = history[1]["tool_calls"][0]["function"]["arguments"]
        self.assertIn("南通市", stored_args)
        self.assertNotIn('"city": "南通"', stored_args)

    def test_query_log_entry_uses_deterministic_turn_key_and_audit_sql(self):
        svc = self._make_service([
            {
                "type": "tool_call",
                "tool_name": "query_soil_summary",
                "tool_args": {
                    "city": "南通市",
                    "start_time": "2025-04-14 00:00:00",
                    "end_time": "2025-04-20 23:59:59",
                },
                "call_id": "call_audit",
            },
            {"type": "text", "content": "南通市最近7天整体偏干。"},
        ])

        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="查南通市最近7天墒情",
            session_id="audit-session",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))

        self.assertEqual(len(result.query_log_entries), 1)
        entry = result.query_log_entries[0]
        self.assertEqual(entry["query_id"], "audit-session:1:0")
        self.assertEqual(entry["session_id"], "audit-session")
        self.assertEqual(entry["turn_id"], 1)
        self.assertEqual(entry["query_type"], "recent_summary")
        self.assertIn("FROM fact_soil_moisture", entry["executed_sql_text"])
        self.assertIn("city = '南通市'", entry["executed_sql_text"])
        self.assertIn("create_time >=", entry["executed_sql_text"])
        self.assertIn("create_time <=", entry["executed_sql_text"])
        self.assertEqual(entry["executed_result_json"]["total_records"], entry["row_count"])

    def test_comparison_query_log_entry_concatenates_multiple_audit_sql_blocks(self):
        svc = self._make_service([
            {
                "type": "tool_call",
                "tool_name": "query_soil_comparison",
                "tool_args": {
                    "entities": ["南通市", "如东县"],
                    "entity_type": "region",
                    "start_time": "2025-04-14 00:00:00",
                    "end_time": "2025-04-20 23:59:59",
                },
                "call_id": "call_cmp",
            },
            {"type": "text", "content": "如东县的风险更高。"},
        ])

        result: AgentLoopResult = asyncio.run(svc.run(
            user_input="对比南通市和如东县最近7天墒情",
            session_id="cmp-session",
            turn_id=1,
            latest_business_time="2025-04-20 08:00:00",
        ))

        self.assertEqual(len(result.query_log_entries), 1)
        entry = result.query_log_entries[0]
        self.assertEqual(entry["query_id"], "cmp-session:1:0")
        self.assertEqual(entry["query_type"], "comparison")
        self.assertIn("-- entity 1", entry["executed_sql_text"])
        self.assertIn("-- entity 2", entry["executed_sql_text"])
        self.assertIn("city = '南通市'", entry["executed_sql_text"])
        self.assertIn("county = '如东县'", entry["executed_sql_text"])
        self.assertEqual(entry["row_count"], 2)

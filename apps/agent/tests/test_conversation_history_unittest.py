import asyncio
from decimal import Decimal
import unittest
from app.repositories.session_context_repository import SessionContextRepository


class ConversationHistoryTest(unittest.TestCase):
    def setUp(self):
        self.repo = SessionContextRepository()

    def test_save_and_load_single_turn(self):
        asyncio.run(self.repo.save_message_turn(
            session_id="s1",
            turn_id=1,
            user_message="查延安市最近7天墒情",
            assistant_message="延安市最近7天整体偏干。",
            tool_calls=[],
            tool_results=[],
        ))
        history = asyncio.run(self.repo.load_history("s1"))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_two_turns_preserve_order(self):
        asyncio.run(self.repo.save_message_turn(
            session_id="s2", turn_id=1,
            user_message="查延安", assistant_message="延安墒情偏干",
            tool_calls=[], tool_results=[],
        ))
        asyncio.run(self.repo.save_message_turn(
            session_id="s2", turn_id=2,
            user_message="那旱情最严重的县是哪个", assistant_message="志丹县最严重",
            tool_calls=[], tool_results=[],
        ))
        history = asyncio.run(self.repo.load_history("s2"))
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["content"], "查延安")
        self.assertEqual(history[2]["content"], "那旱情最严重的县是哪个")

    def test_short_history_is_preserved_until_token_budget(self):
        for i in range(12):
            asyncio.run(self.repo.save_message_turn(
                session_id="s3", turn_id=i + 1,
                user_message=f"问题{i}", assistant_message=f"回答{i}",
                tool_calls=[], tool_results=[],
            ))
        history = asyncio.run(self.repo.load_history("s3"))
        self.assertEqual(len(history), 24)
        self.assertEqual(history[0]["content"], "问题0")
        self.assertEqual(history[-1]["content"], "回答11")

    def test_save_with_tool_calls_stores_them(self):
        asyncio.run(self.repo.save_message_turn(
            session_id="s4", turn_id=1,
            user_message="查延安排名",
            assistant_message="延安志丹县最严重",
            tool_calls=[{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "query_soil_ranking",
                    "arguments": "{\"start_time\": \"2025-04-14 00:00:00\", \"end_time\": \"2025-04-20 23:59:59\", \"aggregation\": \"county\"}",
                },
            }],
            tool_results=[{"items": [{"rank": 1, "name": "志丹县"}]}],
        ))
        history = asyncio.run(self.repo.load_history("s4"))
        self.assertEqual(len(history), 4)
        assistant_msg = history[1]
        tool_msg = history[2]
        self.assertIn("tool_calls", assistant_msg)
        self.assertEqual(assistant_msg["tool_calls"][0]["type"], "function")
        self.assertEqual(assistant_msg["tool_calls"][0]["function"]["name"], "query_soil_ranking")
        self.assertEqual(tool_msg["role"], "tool")
        self.assertEqual(tool_msg["tool_call_id"], "call_1")

    def test_save_with_decimal_tool_result_is_json_safe(self):
        asyncio.run(self.repo.save_message_turn(
            session_id="s4_decimal", turn_id=1,
            user_message="查南通市最近7天详情",
            assistant_message="已完成",
            tool_calls=[{
                "id": "call_decimal_1",
                "type": "function",
                "function": {
                    "name": "query_soil_detail",
                    "arguments": "{\"city\": \"南通市\", \"start_time\": \"2026-04-07 00:00:00\", \"end_time\": \"2026-04-13 23:59:59\"}",
                },
            }],
            tool_results=[{
                "entity_name": "南通市",
                "record_count": 259,
                "latest_record": {"water20cm": Decimal("92.43")},
            }],
        ))
        history = asyncio.run(self.repo.load_history("s4_decimal"))
        tool_msg = history[2]
        payload = __import__("json").loads(tool_msg["content"])
        self.assertEqual(payload["entity_name"], "南通市")
        self.assertEqual(payload["record_count"], 259)
        self.assertEqual(payload["latest_record"]["water20cm"], 92.43)

    def test_clear_removes_all_history(self):
        asyncio.run(self.repo.save_message_turn(
            session_id="s5", turn_id=1,
            user_message="问", assistant_message="答",
            tool_calls=[], tool_results=[],
        ))
        asyncio.run(self.repo.clear_context("s5"))
        history = asyncio.run(self.repo.load_history("s5"))
        self.assertEqual(history, [])

    def test_load_empty_session_returns_empty_list(self):
        history = asyncio.run(self.repo.load_history("nonexistent_session"))
        self.assertEqual(history, [])

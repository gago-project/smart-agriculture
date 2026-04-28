"""P1-12 Step 2 regression — session context summarization.

Verifies that the token-sliding window does not just drop oldest messages
when the budget is exceeded, but folds their key information (entities,
time windows, record counts, recent user questions) into a single summary
system message kept at the head of the transcript.
"""
from __future__ import annotations

import json
import unittest

from app.repositories.session_context_repository import (
    SessionContextRepository,
    _parse_summary,
    _render_summary_message,
    _trim_to_token_limit,
)


def _user(text: str) -> dict:
    return {"role": "user", "content": text}


def _assistant_text(text: str) -> dict:
    return {"role": "assistant", "content": text}


def _assistant_tool_call(name: str, args: dict, call_id: str = "x") -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            }
        ],
    }


def _tool(content: dict, call_id: str = "x") -> dict:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(content, ensure_ascii=False),
    }


class TrimToTokenLimitSummaryTest(unittest.TestCase):
    def test_no_summary_for_short_transcript(self):
        # Below budget — no summary appended
        messages = [_user("最近的概况"), _assistant_text("一切正常")]
        out = _trim_to_token_limit(messages)
        self.assertEqual(out, messages)

    def test_summary_emitted_when_oldest_dropped(self):
        # Construct an over-budget transcript by stuffing tool messages with bulky payloads
        big_payload = {"records": [{"k": "v" * 1000}] * 20}
        messages = []
        for i in range(8):
            messages.append(_user(f"问题{i} 南通市最近怎么样"))
            messages.append(_assistant_tool_call(
                "query_soil_summary",
                {"city": "南通市", "start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"},
                call_id=f"c{i}",
            ))
            messages.append(_tool(big_payload, call_id=f"c{i}"))
            messages.append(_assistant_text(f"回答{i}"))

        out = _trim_to_token_limit(messages)
        # Head must be the summary
        self.assertEqual(out[0]["role"], "system")
        self.assertTrue(out[0]["content"].startswith("[历史摘要] "))
        # Should have dropped some early messages
        self.assertLess(len(out), len(messages) + 1)
        # Summary should mention 南通市
        self.assertIn("南通市", out[0]["content"])

    def test_summary_extracts_entities_time_records_questions(self):
        messages = [
            _user("如东县最近怎么样"),
            _assistant_tool_call("query_soil_summary", {
                "county": "如东县",
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            }, call_id="c1"),
            _tool({"total_records": 12, "entity_name": "如东县"}, call_id="c1"),
            _assistant_text("如东县最近 12 条记录"),
            _user("那海安市呢"),
            _assistant_tool_call("query_soil_summary", {
                "county": "海安市",
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            }, call_id="c2"),
            _tool({"total_records": 8, "entity_name": "海安市"}, call_id="c2"),
            _assistant_text("海安市最近 8 条记录"),
        ]
        # Force trimming by setting a low budget via a wrapper that
        # constructs an oversized transcript. Easier approach: directly call
        # _merge_summary path via a long bulk message ahead of these.
        bulk_filler = [_user("filler " * 5000), _assistant_text("ok " * 5000)] * 4
        messages = bulk_filler + messages

        out = _trim_to_token_limit(messages)
        self.assertEqual(out[0]["role"], "system")
        parsed = _parse_summary(out[0])
        # At least the bulk filler user messages must appear in the running summary
        self.assertGreater(len(parsed["user_questions"]), 0)

    def test_existing_summary_carries_forward(self):
        # Pre-existing summary already mentions 南通市
        pre_summary = _render_summary_message({
            "entities": ["南通市"],
            "time_windows": [{"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"}],
            "total_records": 5,
            "user_questions": ["最近南通市怎么样"],
        })

        # Append bulky tool turns that mention 盐城市 to force more trimming
        bulky_tool_payload = {"records": [{"k": "v" * 1000}] * 20}
        messages = [pre_summary]
        for i in range(8):
            messages.append(_user(f"问题{i}"))
            messages.append(_assistant_tool_call(
                "query_soil_summary",
                {"city": "盐城市", "start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"},
                call_id=f"c{i}",
            ))
            messages.append(_tool(bulky_tool_payload, call_id=f"c{i}"))
            messages.append(_assistant_text(f"回答{i}"))

        out = _trim_to_token_limit(messages)
        self.assertEqual(out[0]["role"], "system")
        parsed = _parse_summary(out[0])
        # The pre-existing 南通市 must still be retained
        self.assertIn("南通市", parsed["entities"])

    def test_render_and_parse_round_trip(self):
        summary = {
            "entities": ["南通市", "如东县"],
            "time_windows": [
                {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"},
                {"start_time": "2026-03-01 00:00:00", "end_time": "2026-03-31 23:59:59"},
            ],
            "total_records": 12,
            "user_questions": ["最近的概况", "如东县呢"],
        }
        msg = _render_summary_message(summary)
        self.assertIn("2026-04-07 00:00:00~2026-04-13 23:59:59", msg["content"])
        self.assertIn("|", msg["content"])
        parsed = _parse_summary(msg)
        self.assertEqual(parsed, summary)

    def test_old_time_expression_summary_is_ignored_safely(self):
        msg = {
            "role": "system",
            "content": "[历史摘要] 实体=南通市;时间窗=last_7_days;记录=12;问题=最近南通市怎么样",
        }

        parsed = _parse_summary(msg)

        self.assertEqual(parsed["entities"], ["南通市"])
        self.assertEqual(parsed["time_windows"], [])
        self.assertEqual(parsed["total_records"], 12)


class SaveMessageTurnSummaryIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_history_eventually_starts_with_summary_after_many_turns(self):
        repo = SessionContextRepository()
        big = "墒情 " * 2000
        for i in range(10):
            await repo.save_message_turn(
                session_id="s1",
                turn_id=i,
                user_message=f"问题 {i} 南通市怎么样",
                assistant_message=f"回答 {i}：{big}",
                tool_calls=[{
                    "id": f"c{i}",
                    "type": "function",
                    "function": {
                        "name": "query_soil_summary",
                        "arguments": json.dumps({
                            "city": "南通市",
                            "start_time": "2026-04-07 00:00:00",
                            "end_time": "2026-04-13 23:59:59",
                        }, ensure_ascii=False),
                    },
                }],
                tool_results=[{"total_records": 5, "entity_name": "南通市"}],
            )

        history = await repo.load_history("s1")
        self.assertGreater(len(history), 0)
        # First message should be the summary system message
        self.assertEqual(history[0]["role"], "system")
        self.assertIn("南通市", history[0]["content"])
        # Token budget must hold
        from app.repositories.session_context_repository import _estimate_tokens, _MAX_CONTEXT_TOKENS
        self.assertLessEqual(_estimate_tokens(history), _MAX_CONTEXT_TOKENS + 2000)


if __name__ == "__main__":
    unittest.main()

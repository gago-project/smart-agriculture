from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.services.semantic_parser_service import SemanticParserService


class SemanticParserServiceContractTest(unittest.TestCase):
    def test_parse_accepts_start_end_contract_and_latest_business_time_context(self) -> None:
        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(return_value={
            "resolved_input": "南京最近13天墒情怎么样",
            "intent_hint": "soil_summary",
            "entities": {"city": "南京市"},
            "start_time": "2026-04-01 00:00:00",
            "end_time": "2026-04-13 23:59:59",
            "needs_clarify": False,
            "clarify_message": "",
        })
        service = SemanticParserService(client)

        result = asyncio.run(service.parse(
            "南京最近13天墒情怎么样",
            [{"role": "assistant", "content": "上一轮是最近7天"}],
            latest_business_time="2026-04-13 23:59:17",
        ))

        self.assertEqual(result.entities["city"], "南京市")
        self.assertEqual(result.start_time, "2026-04-01 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")
        sent_messages = client._request_json.await_args.kwargs["messages"]
        self.assertIn("2026-04-13 23:59:17", sent_messages[0]["content"])

    def test_default_timeout_allows_slightly_slow_llm_parse(self) -> None:
        class SlowClient:
            def available(self):
                return True

            async def _request_json(self, *, messages):
                await asyncio.sleep(3.2)
                return {
                    "resolved_input": "SNS00204333 最近 7 天怎么样",
                    "intent_hint": "soil_detail",
                    "entities": {"sn": "SNS00204333"},
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                    "needs_clarify": False,
                    "clarify_message": "",
                }

        service = SemanticParserService(SlowClient())

        result = asyncio.run(service.parse(
            "SNS00204333 最近 7 天怎么样",
            [],
            latest_business_time="2026-04-13 23:59:17",
        ))

        self.assertEqual(result.intent_hint, "soil_detail")
        self.assertEqual(result.entities["sn"], "SNS00204333")


if __name__ == "__main__":
    unittest.main()

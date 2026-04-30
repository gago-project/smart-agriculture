from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock


class LlmFollowUpResolverServiceTest(unittest.TestCase):
    def test_returns_structured_result_when_llm_marks_follow_up(self) -> None:
        from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "is_follow_up": True,
                "operation": "replace_slot",
                "new_slots": {"county": "海安市"},
                "inherit_slots": ["time"],
                "confidence": 0.91,
            }
        )

        service = LlmFollowUpResolverService(client)
        result = asyncio.run(service.resolve(text="那海安市呢", context={}, latest_target=None))

        self.assertTrue(result.is_follow_up)
        self.assertEqual(result.operation, "replace_slot")
        self.assertEqual(result.new_slots["county"], "海安市")
        self.assertEqual(result.confidence, 0.91)

    def test_timeout_falls_back_to_none(self) -> None:
        from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService

        class SlowClient:
            def available(self):
                return True

            async def _request_json(self, *, messages):
                del messages
                await asyncio.sleep(0.05)
                return {"is_follow_up": True, "operation": "inherit", "new_slots": {}, "inherit_slots": ["time"], "confidence": 0.9}

        service = LlmFollowUpResolverService(SlowClient(), timeout_seconds=0.01)
        result = asyncio.run(service.resolve(text="最近一个月", context={}, latest_target=None))

        self.assertIsNone(result)

    def test_invalid_json_falls_back_to_none(self) -> None:
        from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(return_value={"foo": "bar"})

        service = LlmFollowUpResolverService(client)
        result = asyncio.run(service.resolve(text="最近一个月", context={}, latest_target=None))

        self.assertIsNone(result)

    def test_unavailable_client_falls_back_to_none(self) -> None:
        from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService

        client = MagicMock()
        client.available.return_value = False

        service = LlmFollowUpResolverService(client)
        result = asyncio.run(service.resolve(text="最近一个月", context={}, latest_target=None))

        self.assertIsNone(result)

    def test_low_confidence_result_is_preserved(self) -> None:
        from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "is_follow_up": True,
                "operation": "inherit",
                "new_slots": {},
                "inherit_slots": ["time"],
                "confidence": 0.42,
            }
        )

        service = LlmFollowUpResolverService(client)
        result = asyncio.run(service.resolve(text="最近一个月", context={}, latest_target=None))

        self.assertIsNotNone(result)
        self.assertEqual(result.confidence, 0.42)

    def test_allow_result_is_returned_as_non_follow_up(self) -> None:
        from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "is_follow_up": False,
                "operation": "standalone",
                "new_slots": {},
                "inherit_slots": [],
                "confidence": 0.88,
            }
        )

        service = LlmFollowUpResolverService(client)
        result = asyncio.run(service.resolve(text="查一下南通的情况", context={}, latest_target=None))

        self.assertIsNotNone(result)
        self.assertFalse(result.is_follow_up)
        self.assertEqual(result.operation, "standalone")


if __name__ == "__main__":
    unittest.main()

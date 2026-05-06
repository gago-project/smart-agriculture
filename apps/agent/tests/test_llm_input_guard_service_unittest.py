from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock


class LlmInputGuardServiceContractTest(unittest.TestCase):
    def test_returns_out_of_domain_when_llm_marks_noise(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "category": "out_of_domain",
                "confidence": 0.92,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.category, "out_of_domain")
        self.assertAlmostEqual(result.confidence, 0.92)

    def test_returns_allow_result_when_llm_marks_business(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "category": "allow",
                "confidence": 0.88,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("查一下南通的情况"))

        self.assertEqual(result.category, "allow")
        self.assertAlmostEqual(result.confidence, 0.88)

    def test_returns_greeting_category(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "category": "greeting",
                "confidence": 0.97,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("哈喽"))

        self.assertEqual(result.category, "greeting")
        self.assertAlmostEqual(result.confidence, 0.97)

    def test_returns_capability_question_category(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "category": "capability_question",
                "confidence": 0.91,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("你有什么本领"))

        self.assertEqual(result.category, "capability_question")
        self.assertAlmostEqual(result.confidence, 0.91)

    def test_timeout_falls_back_to_allow(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        class SlowClient:
            def available(self):
                return True

            async def _request_json(self, *, messages):
                del messages
                await asyncio.sleep(0.05)
                return {
                    "category": "out_of_domain",
                    "confidence": 0.95,
                }

        service = LlmInputGuardService(SlowClient(), timeout_seconds=0.01)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.category, "allow")
        self.assertEqual(result.confidence, 0.0)

    def test_invalid_json_shape_falls_back_to_allow(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(return_value={"foo": "bar"})

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.category, "allow")
        self.assertEqual(result.confidence, 0.0)

    def test_unavailable_client_falls_back_to_allow(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = False

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.category, "allow")
        self.assertEqual(result.confidence, 0.0)

    def test_low_confidence_result_is_preserved_for_caller_thresholding(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "category": "out_of_domain",
                "confidence": 0.45,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("京东卡可以提现吗"))

        self.assertEqual(result.category, "out_of_domain")
        self.assertAlmostEqual(result.confidence, 0.45)


if __name__ == "__main__":
    unittest.main()

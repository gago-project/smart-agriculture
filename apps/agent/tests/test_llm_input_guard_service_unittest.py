from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock


class LlmInputGuardServiceContractTest(unittest.TestCase):
    def test_returns_intercept_result_when_llm_marks_noise(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "decision": "intercept",
                "reason": "noise",
                "confidence": 0.92,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.decision, "intercept")
        self.assertEqual(result.reason, "noise")
        self.assertEqual(result.confidence, 0.92)

    def test_returns_allow_result_when_llm_marks_business(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "decision": "allow",
                "reason": "noise",
                "confidence": 0.88,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("查一下南通的情况"))

        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.confidence, 0.88)

    def test_timeout_falls_back_to_allow(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        class SlowClient:
            def available(self):
                return True

            async def _request_json(self, *, messages):
                del messages
                await asyncio.sleep(0.05)
                return {
                    "decision": "intercept",
                    "reason": "noise",
                    "confidence": 0.95,
                }

        service = LlmInputGuardService(SlowClient(), timeout_seconds=0.01)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.confidence, 0.0)

    def test_invalid_json_shape_falls_back_to_allow(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(return_value={"foo": "bar"})

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.confidence, 0.0)

    def test_unavailable_client_falls_back_to_allow(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = False

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("上岛咖啡京东卡"))

        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.confidence, 0.0)

    def test_low_confidence_result_is_preserved_for_caller_thresholding(self) -> None:
        from app.services.llm_input_guard_service import LlmInputGuardService

        client = MagicMock()
        client.available.return_value = True
        client._request_json = AsyncMock(
            return_value={
                "decision": "intercept",
                "reason": "off_topic",
                "confidence": 0.45,
            }
        )

        service = LlmInputGuardService(client)
        result = asyncio.run(service.classify("京东卡可以提现吗"))

        self.assertEqual(result.decision, "intercept")
        self.assertEqual(result.reason, "off_topic")
        self.assertEqual(result.confidence, 0.45)


if __name__ == "__main__":
    unittest.main()

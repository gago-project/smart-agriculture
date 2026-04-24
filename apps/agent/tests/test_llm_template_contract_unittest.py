"""Unit tests for llm template contract."""

from __future__ import annotations

import asyncio
from decimal import Decimal
import json
import unittest

from app.llm.qwen_client import QwenClient
from app.schemas.state import QueryResultBundle
from app.services.intent_slot_service import IntentSlotService
from app.services.response_service import ResponseService
from app.services.template_service import TemplateService


class FakeQwenClient:
    """Test double for fake qwen client."""
    def available(self) -> bool:
        """Return whether this test double should be treated as available."""
        return True

    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        """Handle extract intent slots on the fake qwen client."""
        del user_input, session_id
        return {
            "intent": "soil_recent_summary",
            "answer_type": "soil_summary_answer",
            "slots": {"time_range": "last_7_days"},
        }

    async def generate_controlled_answer(self, **kwargs):
        """Handle generate controlled answer on the fake qwen client."""
        del kwargs
        return "这是来自千问受控生成的回答。"


class FakeInvalidQwenClient(FakeQwenClient):
    """Test double for fake invalid qwen client."""
    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        """Handle extract intent slots on the fake invalid qwen client."""
        del user_input, session_id
        return {
            "intent": "查询土壤墒情异常",
            "answer_type": "详情回答",
            "slots": {},
        }


class FakeClarifyingQwenClient(FakeQwenClient):
    """Test double for fake clarifying qwen client."""
    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        """Handle extract intent slots on the fake clarifying qwen client."""
        del user_input, session_id
        return {
            "intent": "clarification_needed",
            "answer_type": "clarification_answer",
            "slots": {},
        }


class FakeRegionRepository:
    """Repository helper for fake region."""
    async def region_alias_rows_async(self):
        """Return region alias rows async."""
        return []

    async def known_region_names_async(self):
        """Handle known region names async on the fake region repository."""
        return set()


class CapturingQwenClient(QwenClient):
    """Real Qwen client path with request capture and no real network IO."""

    def __init__(self) -> None:
        """Initialize with a non-empty api key so generation path is exercised."""
        super().__init__(api_key="test-key")
        self.last_messages: list[dict[str, str]] | None = None

    async def _request_json(self, *, messages: list[dict[str, str]]):
        """Capture serialized messages and return a stable response."""
        self.last_messages = messages
        return {"final_answer": "captured-qwen-answer"}


class LlmTemplateContractTest(unittest.TestCase):
    """Test cases for llm template contract."""
    def test_intent_slot_service_can_use_qwen_result(self) -> None:
        """Verify intent slot service can use qwen result."""
        async def run_case() -> None:
            service = IntentSlotService(repository=FakeRegionRepository(), qwen_client=FakeQwenClient())
            result = await service.parse("最近墒情怎么样", "session-1")
            self.assertEqual(result.intent, "soil_recent_summary")
            self.assertEqual(result.answer_type, "soil_summary_answer")
            self.assertEqual(result.slots["time_range"], "last_7_days")

        asyncio.run(run_case())

    def test_intent_slot_service_rejects_invalid_qwen_enum_and_falls_back(self) -> None:
        """Verify intent slot service rejects invalid qwen enum and falls back."""
        async def run_case() -> None:
            service = IntentSlotService(repository=FakeRegionRepository(), qwen_client=FakeInvalidQwenClient())
            result = await service.parse("SNS00204333 最近有没有异常", "session-1")
            self.assertEqual(result.intent, "soil_device_query")
            self.assertEqual(result.answer_type, "soil_detail_answer")
            self.assertEqual(result.slots["sn"], "SNS00204333")

        asyncio.run(run_case())

    def test_intent_slot_service_prefers_deterministic_follow_up_over_qwen_clarify(self) -> None:
        """Verify intent slot service prefers deterministic follow up over qwen clarify."""
        async def run_case() -> None:
            service = IntentSlotService(repository=FakeRegionRepository(), qwen_client=FakeClarifyingQwenClient())
            result = await service.parse("那上周的呢", "session-1")
            self.assertEqual(result.intent, "soil_region_query")
            self.assertEqual(result.answer_type, "soil_detail_answer")
            self.assertEqual(result.slots["time_range"], "last_week")
            self.assertTrue(result.slots["follow_up"])

        asyncio.run(run_case())

    def test_response_service_can_use_qwen_draft(self) -> None:
        """Verify response service can use qwen draft."""
        async def run_case() -> None:
            service = ResponseService(qwen_client=FakeQwenClient())
            result = await service.generate(
                intent="soil_recent_summary",
                answer_type="soil_summary_answer",
                query_result={"records": [{"create_time": "2026-04-21 09:00:00", "water20cm": 66, "soil_status": "not_triggered"}]},
                rule_result={"evaluated_records": [{"create_time": "2026-04-21 09:00:00", "water20cm": 66, "soil_status": "not_triggered"}]},
                template_result={},
                advice_result={},
                slots={},
                business_time={"latest_business_time": "2026-04-21 09:00:00"},
            )
            self.assertEqual(result["final_answer"], "这是来自千问受控生成的回答。")

        asyncio.run(run_case())

    def test_qwen_client_can_serialize_bundle_models_with_decimal_facts(self) -> None:
        """Verify controlled-answer payload handles bundle models and decimals."""
        async def run_case() -> None:
            client = CapturingQwenClient()
            answer = await client.generate_controlled_answer(
                answer_type="soil_detail_answer",
                fallback_answer="fallback",
                facts={
                    "query_result": QueryResultBundle(
                        records=[{"sn": "SNS00204333", "water20cm": Decimal("66.10")}]
                    )
                },
            )

            self.assertEqual(answer, "captured-qwen-answer")
            self.assertIsNotNone(client.last_messages)
            payload = json.loads(client.last_messages[1]["content"])
            self.assertEqual(payload["facts"]["query_result"]["records"][0]["sn"], "SNS00204333")
            self.assertEqual(payload["facts"]["query_result"]["records"][0]["water20cm"], 66.1)

        asyncio.run(run_case())

    def test_template_service_renders_with_jinja_templates(self) -> None:
        """Verify template service renders with jinja templates."""
        service = TemplateService(repository=FakeRegionRepository())
        result = service.render(
            answer_type="soil_warning_answer",
            query_result={"records": [{"create_time": "2026-04-21 09:00:00", "city": "南京市", "county": "玄武区", "sn": "SNS00204333", "water20cm": 44, "display_label": "重旱"}]},
            rule_result={"evaluated_records": [{"create_time": "2026-04-21 09:00:00", "city": "南京市", "county": "玄武区", "sn": "SNS00204333", "water20cm": 44, "display_label": "重旱", "soil_status": "heavy_drought"}], "route_action": "template_only"},
            slots={"render_mode": "strict"},
        )
        self.assertIn("SNS00204333", result["rendered_text"])
        self.assertIn("南京市", result["rendered_text"])


if __name__ == "__main__":
    unittest.main()

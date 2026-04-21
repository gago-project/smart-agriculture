from __future__ import annotations

import asyncio
import unittest

from app.services.intent_slot_service import IntentSlotService
from app.services.response_service import ResponseService
from app.services.template_service import TemplateService


class FakeQwenClient:
    def available(self) -> bool:
        return True

    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        del user_input, session_id
        return {
            "intent": "soil_recent_summary",
            "answer_type": "soil_summary_answer",
            "slots": {"time_range": "last_7_days"},
        }

    async def generate_controlled_answer(self, **kwargs):
        del kwargs
        return "这是来自千问受控生成的回答。"


class FakeInvalidQwenClient(FakeQwenClient):
    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        del user_input, session_id
        return {
            "intent": "查询土壤墒情异常",
            "answer_type": "详情回答",
            "slots": {},
        }


class FakeRegionRepository:
    async def region_alias_rows_async(self):
        return []

    async def known_region_names_async(self):
        return set()


class LlmTemplateContractTest(unittest.TestCase):
    def test_intent_slot_service_can_use_qwen_result(self) -> None:
        async def run_case() -> None:
            service = IntentSlotService(repository=FakeRegionRepository(), qwen_client=FakeQwenClient())
            result = await service.parse("最近墒情怎么样", "session-1")
            self.assertEqual(result.intent, "soil_recent_summary")
            self.assertEqual(result.answer_type, "soil_summary_answer")
            self.assertEqual(result.slots["time_range"], "last_7_days")

        asyncio.run(run_case())

    def test_intent_slot_service_rejects_invalid_qwen_enum_and_falls_back(self) -> None:
        async def run_case() -> None:
            service = IntentSlotService(repository=FakeRegionRepository(), qwen_client=FakeInvalidQwenClient())
            result = await service.parse("SNS00204333 最近有没有异常", "session-1")
            self.assertEqual(result.intent, "soil_device_query")
            self.assertEqual(result.answer_type, "soil_detail_answer")
            self.assertEqual(result.slots["device_sn"], "SNS00204333")

        asyncio.run(run_case())

    def test_response_service_can_use_qwen_draft(self) -> None:
        async def run_case() -> None:
            service = ResponseService(qwen_client=FakeQwenClient())
            result = await service.generate(
                intent="soil_recent_summary",
                answer_type="soil_summary_answer",
                query_result={"records": [{"sample_time": "2026-04-21 09:00:00", "water20cm": 66, "soil_status": "not_triggered"}]},
                rule_result={"evaluated_records": [{"sample_time": "2026-04-21 09:00:00", "water20cm": 66, "soil_status": "not_triggered"}]},
                template_result={},
                advice_result={},
                slots={},
                business_time={"latest_business_time": "2026-04-21 09:00:00"},
            )
            self.assertEqual(result["final_answer"], "这是来自千问受控生成的回答。")

        asyncio.run(run_case())

    def test_template_service_renders_with_jinja_templates(self) -> None:
        service = TemplateService(repository=FakeRegionRepository())
        result = service.render(
            answer_type="soil_warning_answer",
            query_result={"records": [{"sample_time": "2026-04-21 09:00:00", "city_name": "南京市", "county_name": "玄武区", "device_sn": "SNS00204333", "water20cm": 44, "display_label": "重旱"}]},
            rule_result={"evaluated_records": [{"sample_time": "2026-04-21 09:00:00", "city_name": "南京市", "county_name": "玄武区", "device_sn": "SNS00204333", "water20cm": 44, "display_label": "重旱", "soil_status": "heavy_drought"}], "route_action": "template_only"},
            slots={"render_mode": "strict"},
        )
        self.assertIn("SNS00204333", result["rendered_text"])
        self.assertIn("南京市", result["rendered_text"])


if __name__ == "__main__":
    unittest.main()

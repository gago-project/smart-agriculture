"""需求 #9 预警处置查询单元测试。"""

from __future__ import annotations

import unittest

from app.services.data_answer_service import DataAnswerService
from app.services.follow_up_action_resolver_service import FollowUpActionResult
from app.services.time_window_service import TimeWindowResolution
from app.services.turn_route_decision_service import TurnRouteDecisionService
from tests.support_repositories import SeedSoilRepository


def _entities(city: str | None = None, county: str | None = None) -> dict:
    return {
        "city": [city] if city else [],
        "county": [county] if county else [],
        "sn": [],
        "province": [],
        "resolved": [],
    }


def _time_window(
    *,
    matched: bool = True,
    has_signal: bool = True,
    start: str | None = None,
    end: str | None = None,
) -> TimeWindowResolution:
    return TimeWindowResolution(
        matched=matched,
        has_time_signal=has_signal,
        time_source="rule_relative" if matched or has_signal else None,
        start_time=start or "2026-04-01 00:00:00",
        end_time=end or "2026-04-30 23:59:59",
    )


class WarningDisposalSeedRepository(SeedSoilRepository):
    def __init__(self, stats: dict[str, int] | None = None) -> None:
        super().__init__()
        self.warning_disposal_stats = stats or {
            "total": 11,
            "已处理": 7,
            "待处理": 2,
            "超时已处理": 1,
            "超时待处理": 1,
        }
        self.warning_disposal_calls: list[dict[str, str | None]] = []
        self.extra_region_aliases = [
            {
                "alias_name": "南通市",
                "canonical_name": "南通市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "canonical",
            },
            {
                "alias_name": "南通",
                "canonical_name": "南通市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "seed",
            },
        ]

    async def query_warning_disposal_stats_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, int]:
        self.warning_disposal_calls.append(
            {
                "city": city,
                "county": county,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        return dict(self.warning_disposal_stats)


class TestWarningDisposalRouting(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TurnRouteDecisionService()

    def test_basic_disposal_query(self) -> None:
        result = self.service.decide(
            message="最近30天全省预警处置情况怎么样",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_disposal")
        self.assertEqual(result.query_shape.subject, "warning_disposal")
        self.assertEqual(result.query_shape.action, "stats")

    def test_disposal_with_city_entity(self) -> None:
        result = self.service.decide(
            message="上周南通市的预警处置进度如何",
            current_context={},
            entities=_entities(city="南通市"),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_disposal")

    def test_warning_list_not_disposal(self) -> None:
        result = self.service.decide(
            message="最近7天哪些区域出现了预警信息",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )
        self.assertNotEqual(result.route, "warning_disposal")

    def test_warning_rule_not_disposal(self) -> None:
        result = self.service.decide(
            message="预警规则是什么",
            current_context={},
            entities=_entities(),
            time_evidence=TimeWindowResolution(),
            action_result=FollowUpActionResult(),
        )
        self.assertNotEqual(result.route, "warning_disposal")

    def test_is_warning_disposal_query_detection(self) -> None:
        svc = TurnRouteDecisionService
        self.assertTrue(svc._is_warning_disposal_query("最近30天预警处置情况"))
        self.assertTrue(svc._is_warning_disposal_query("已处理多少条预警"))
        self.assertTrue(svc._is_warning_disposal_query("上周预警处置进度"))
        self.assertTrue(svc._is_warning_disposal_query("超时未处理的预警"))
        self.assertFalse(svc._is_warning_disposal_query("最近7天哪些区域出现预警"))
        self.assertFalse(svc._is_warning_disposal_query("预警规则是什么"))


class TestWarningDisposalAnswer(unittest.IsolatedAsyncioTestCase):
    async def test_reply_warning_disposal_returns_fixed_status_order(self) -> None:
        repository = WarningDisposalSeedRepository(
            stats={
                "total": 10,
                "已处理": 7,
                "待处理": 1,
                "超时已处理": 1,
                "超时待处理": 1,
            }
        )
        service = DataAnswerService(repository=repository)

        result = await service.reply(
            message="最近30天全省预警处置情况怎么样",
            session_id="warning-disposal",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(result["answer_kind"], "business")
        self.assertEqual(result["capability"], "warning_disposal")
        self.assertIn("内共出现 10 条墒情预警信息，处置情况如下", result["final_text"])
        self.assertIn("已处理 7 条，待处理 1 条，超时已处理 1 条，超时待处理 1 条。", result["final_text"])
        self.assertEqual(result["blocks"][0]["block_type"], "warning_disposal_card")
        self.assertEqual(result["blocks"][0]["stats"], {"已处理": 7, "待处理": 1, "超时已处理": 1, "超时待处理": 1})
        self.assertEqual(result["query_log_entries"][0]["query_type"], "warning_disposal")
        self.assertIn("FROM warning_disposal_record", result["query_log_entries"][0]["executed_sql_text"])
        self.assertEqual(result["query_log_entries"][0]["row_count"], 1)

    async def test_reply_warning_disposal_no_data_text(self) -> None:
        repository = WarningDisposalSeedRepository(
            stats={
                "total": 0,
                "已处理": 0,
                "待处理": 0,
                "超时已处理": 0,
                "超时待处理": 0,
            }
        )
        service = DataAnswerService(repository=repository)

        result = await service.reply(
            message="2099年1月1日到1月31日全省预警处置情况怎么样",
            session_id="warning-disposal-empty",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(result["answer_kind"], "business")
        self.assertEqual(result["capability"], "warning_disposal")
        self.assertIn("内未查询到有效墒情预警信息，无对应处置数据", result["final_text"])
        self.assertEqual(result["blocks"][0]["total"], 0)


if __name__ == "__main__":
    unittest.main()

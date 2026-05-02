from __future__ import annotations

import unittest

from tests.support_repositories import SeedSoilRepository
from app.services.soil_evidence_deriver_service import SoilEvidenceDeriverService
from app.services.tool_executor_service import ToolExecutorService


class SoilEvidenceDeriverServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repo = SeedSoilRepository()
        self.executor = ToolExecutorService(repository=self.repo)
        self.service = SoilEvidenceDeriverService(repository=self.repo)

    async def test_summary_profile_uses_warning_regions_instead_of_raw_volume_regions(self) -> None:
        resolved_args = {
            "start_time": "2026-04-07 00:00:00",
            "end_time": "2026-04-13 23:59:59",
            "output_mode": "normal",
        }
        raw_result = await self.executor.execute(
            tool_name="query_soil_summary",
            tool_args=resolved_args,
        )

        profile = await self.service.derive(
            tool_name="query_soil_summary",
            user_input="最近 7 天整体墒情怎么样",
            raw_result=raw_result,
            raw_args={},
            resolved_args=resolved_args,
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
            resolver_warnings=[],
        )

        self.assertEqual(profile["derived_summary"]["alert_count"], 44)
        self.assertEqual(
            [item["region"] for item in profile["derived_summary"]["attention_regions"][:3]],
            ["睢宁县", "沛县", "昆山市"],
        )
        self.assertIn("睢宁县", profile["must_surface_facts"])
        self.assertEqual(profile["display_focus"], "normal")

    async def test_ranking_profile_uses_severity_basis_not_raw_record_count(self) -> None:
        resolved_args = {
            "aggregation": "county",
            "top_n": 5,
            "start_time": "2026-03-15 00:00:00",
            "end_time": "2026-04-13 23:59:59",
        }
        raw_result = await self.executor.execute(
            tool_name="query_soil_ranking",
            tool_args=resolved_args,
        )

        profile = await self.service.derive(
            tool_name="query_soil_ranking",
            user_input="最近 30 天县区里哪几个最严重",
            raw_result=raw_result,
            raw_args={},
            resolved_args=resolved_args,
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
            resolver_warnings=[],
        )

        severity_items = profile["derived_summary"]["severity_items"]
        self.assertEqual(profile["severity_basis"], "alert_record_count")
        self.assertEqual(
            [(item["name"], item["alert_record_count"]) for item in severity_items[:3]],
            [("睢宁县", 39), ("昆山市", 37), ("沛县", 36)],
        )
        self.assertNotIn("全局", profile["must_surface_facts"])

    async def test_city_ranking_profile_does_not_leak_county_context_into_must_surface_facts(self) -> None:
        resolved_args = {
            "aggregation": "city",
            "top_n": 5,
            "start_time": "2026-03-15 00:00:00",
            "end_time": "2026-04-13 23:59:59",
        }
        raw_result = await self.executor.execute(
            tool_name="query_soil_ranking",
            tool_args=resolved_args,
        )

        profile = await self.service.derive(
            tool_name="query_soil_ranking",
            user_input="最近 30 天市级层面哪里最需要关注",
            raw_result=raw_result,
            raw_args={},
            resolved_args=resolved_args,
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
            resolver_warnings=[],
        )

        first_item = profile["derived_summary"]["severity_items"][0]
        self.assertEqual(first_item["name"], "徐州市")
        self.assertIsNone(first_item["county"])
        self.assertIn("徐州市", profile["must_surface_facts"])
        self.assertNotIn("徐州市睢宁县", profile["must_surface_facts"])

    async def test_detail_profile_retains_warning_sample_and_recent_abnormal_period(self) -> None:
        resolved_args = {
            "sn": "SNS00204334",
            "start_time": "2026-01-01 00:00:00",
            "end_time": "2026-04-13 23:59:59",
            "output_mode": "advice_mode",
        }
        raw_result = await self.executor.execute(
            tool_name="query_soil_detail",
            tool_args=resolved_args,
        )

        profile = await self.service.derive(
            tool_name="query_soil_detail",
            user_input="SNS00204334 这种情况需要注意什么",
            raw_result=raw_result,
            raw_args={"sn": "SNS00204334", "output_mode": "advice_mode"},
            resolved_args=resolved_args,
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
            resolver_warnings=[],
        )

        abnormal_period = profile["derived_summary"]["abnormal_period"]
        self.assertEqual(profile["display_focus"], "advice_mode")
        self.assertEqual(profile["representative_records"]["latest_warning_record"]["sn"], "SNS00204334")
        self.assertEqual(abnormal_period["start_time"], "2026-01-10 23:59:17")
        self.assertEqual(abnormal_period["end_time"], "2026-01-14 23:59:17")
        self.assertIn("2026-01-10", profile["must_surface_facts"])
        self.assertIn("2026-01-14", profile["must_surface_facts"])

    async def test_comparison_profile_uses_warning_counts_to_pick_winner(self) -> None:
        resolved_args = {
            "entity_type": "region",
            "entities": [
                {
                    "raw_name": "睢宁县",
                    "canonical_name": "睢宁县",
                    "level": "county",
                    "parent_city_name": "徐州市",
                },
                {
                    "raw_name": "沛县",
                    "canonical_name": "沛县",
                    "level": "county",
                    "parent_city_name": "徐州市",
                },
            ],
            "start_time": "2026-03-15 00:00:00",
            "end_time": "2026-04-13 23:59:59",
        }
        raw_result = await self.executor.execute(
            tool_name="query_soil_comparison",
            tool_args=resolved_args,
        )

        profile = await self.service.derive(
            tool_name="query_soil_comparison",
            user_input="睢宁县和沛县最近30天哪边更严重",
            raw_result=raw_result,
            raw_args={"entities": ["睢宁县", "沛县"], "entity_type": "region"},
            resolved_args=resolved_args,
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
            resolver_warnings=[],
        )

        self.assertEqual(profile["severity_basis"], "alert_record_count")
        self.assertEqual(profile["derived_summary"]["winner"], "睢宁县")
        self.assertEqual(
            [(item["name"], item["alert_record_count"]) for item in profile["derived_summary"]["comparison_items"][:2]],
            [("睢宁县", 39), ("沛县", 36)],
        )

    async def test_entity_resolution_trace_preserves_medium_confidence_alias_notice(self) -> None:
        resolved_args = {
            "city": "南通市",
            "start_time": "2026-04-07 00:00:00",
            "end_time": "2026-04-13 23:59:59",
            "output_mode": "normal",
        }
        raw_result = await self.executor.execute(
            tool_name="query_soil_summary",
            tool_args=resolved_args,
        )

        profile = await self.service.derive(
            tool_name="query_soil_summary",
            user_input="查一下南通的情况",
            raw_result=raw_result,
            raw_args={"city": "南通"},
            resolved_args=resolved_args,
            entity_confidence="medium",
            time_source="default_recent_7d",
            used_context=False,
            context_correction=False,
            resolver_warnings=["地区名称 '南通' 已近似匹配为 '南通市'"],
        )

        trace = profile["entity_resolution_trace"]
        self.assertEqual(trace["raw_scope"]["city"], "南通")
        self.assertEqual(trace["resolved_scope"]["city"], "南通市")
        self.assertEqual(trace["entity_confidence"], "medium")
        self.assertIn("置信度中", trace["confidence_notice"])


if __name__ == "__main__":
    unittest.main()

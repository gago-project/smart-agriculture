"""Unit tests for deterministic raw-only business answer rendering."""

from __future__ import annotations

import unittest

from app.services.business_answer_renderer import BusinessAnswerRenderer


class BusinessAnswerRendererTest(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = BusinessAnswerRenderer()

    def test_summary_renderer_uses_derived_attention_regions_and_stability_conclusion(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            answer_evidence_profile={
                "entity_name": "全局",
                "display_focus": "normal",
                "time_window": {
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": ""},
                "derived_summary": {
                    "total_records": 3689,
                    "device_count": 527,
                    "region_count": 80,
                    "avg_water20cm": 93.77,
                    "latest_create_time": "2026-04-13 23:59:17",
                    "stability_conclusion": "整体仍以未触发预警为主",
                    "alert_count": 44,
                    "attention_regions": [
                        {"region": "睢宁县", "alert_record_count": 9},
                        {"region": "沛县", "alert_record_count": 8},
                        {"region": "昆山市", "alert_record_count": 7},
                    ],
                    "dominant_warning_type": "涝渍",
                },
                "must_surface_facts": ["睢宁县", "沛县", "昆山市"],
            },
        )

        self.assertIn("整体仍以未触发预警为主", text)
        self.assertIn("44 条预警相关记录", text)
        self.assertIn("睢宁县", text)
        self.assertIn("沛县", text)
        self.assertIn("昆山市", text)

    def test_summary_renderer_includes_medium_confidence_notice(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            answer_evidence_profile={
                "entity_name": "南通市",
                "display_focus": "normal",
                "time_window": {
                    "start_time": "2026-04-01 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": "按近似匹配识别为 南通市，置信度中。"},
                "derived_summary": {
                    "total_records": 259,
                    "device_count": 37,
                    "region_count": 6,
                    "avg_water20cm": 95.39,
                    "latest_create_time": "2026-04-13 23:59:17",
                    "stability_conclusion": "总体平稳",
                    "alert_count": 0,
                    "attention_regions": [],
                },
                "must_surface_facts": ["南通市", "置信度"],
            },
        )

        self.assertIn("南通市", text)
        self.assertIn("置信度中", text)

    def test_summary_renderer_in_advice_mode_mentions_recommendation(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            answer_evidence_profile={
                "entity_name": "南通市",
                "display_focus": "advice_mode",
                "time_window": {
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": ""},
                "derived_summary": {
                    "total_records": 259,
                    "device_count": 37,
                    "region_count": 6,
                    "avg_water20cm": 95.39,
                    "latest_create_time": "2026-04-13 23:59:17",
                    "stability_conclusion": "总体平稳",
                    "alert_count": 0,
                    "attention_regions": [],
                    "dominant_warning_type": "",
                },
                "must_surface_facts": ["南通市", "总体平稳"],
            },
        )

        self.assertIn("总体平稳", text)
        self.assertIn("建议", text)
        self.assertIn("巡检", text)

    def test_detail_renderer_uses_representative_alert_and_abnormal_period(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_detail",
            answer_evidence_profile={
                "entity_name": "SNS00204333",
                "entity_type": "device",
                "display_focus": "advice_mode",
                "time_window": {
                    "start_time": "2026-01-01 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": "", "used_context": True},
                "derived_summary": {
                    "record_count": 103,
                    "avg_water20cm": 71.97,
                    "latest_record_digest": {
                        "latest_time": "2026-04-13 23:59:17",
                        "location": "南通市如东县",
                        "water20cm": "84.00",
                    },
                    "dominant_warning_type": "重旱",
                    "abnormal_period": {
                        "start_time": "2026-01-10 23:59:17",
                        "end_time": "2026-01-14 23:59:17",
                    },
                    "historical_recovery_hint": "当前最新记录已恢复到未触发预警状态",
                },
                "representative_records": {
                    "latest_warning_record": {
                        "sn": "SNS00204334",
                        "warning_level_label": "重旱",
                    }
                },
                "must_surface_facts": ["2026-01-10", "2026-01-14"],
            },
        )

        self.assertIn("2026-01-10", text)
        self.assertIn("2026-01-14", text)
        self.assertIn("当前最新记录已恢复到未触发预警状态", text)
        self.assertIn("重旱", text)

    def test_detail_renderer_mentions_context_correction_and_location(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_detail",
            answer_evidence_profile={
                "entity_name": "如皋市",
                "entity_type": "region",
                "display_focus": "normal",
                "time_window": {
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {
                    "confidence_notice": "",
                    "used_context": True,
                    "context_correction": True,
                },
                "derived_summary": {
                    "record_count": 28,
                    "avg_water20cm": 128.98,
                    "latest_record_digest": {
                        "latest_time": "2026-04-13 23:59:17",
                        "location": "南通市如皋市",
                        "water20cm": "128.98",
                    },
                },
                "representative_records": {},
                "must_surface_facts": ["如皋市"],
            },
        )

        self.assertIn("已切换到如皋市", text)
        self.assertIn("沿用最近 7 天", text)
        self.assertIn("南通市如皋市", text)

    def test_comparison_renderer_mentions_severity_winner_and_counts(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_comparison",
            answer_evidence_profile={
                "entity_name": "睢宁县和沛县",
                "display_focus": "normal",
                "severity_basis": "alert_record_count",
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": ""},
                "derived_summary": {
                    "winner": "睢宁县",
                    "comparison_items": [
                        {"name": "睢宁县", "alert_record_count": 39, "dominant_warning_type": "涝渍"},
                        {"name": "沛县", "alert_record_count": 36, "dominant_warning_type": "涝渍"},
                    ],
                },
                "must_surface_facts": ["睢宁县", "39", "36"],
            },
        )

        self.assertIn("睢宁县", text)
        self.assertIn("沛县", text)
        self.assertIn("39", text)
        self.assertIn("36", text)
        self.assertIn("更严重", text)

    def test_ranking_renderer_mentions_severity_counts_and_device_region_context(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_ranking",
            answer_evidence_profile={
                "entity_name": "设备排行",
                "display_focus": "normal",
                "severity_basis": "alert_record_count",
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": ""},
                "derived_summary": {
                    "aggregation": "device",
                    "severity_items": [
                        {"name": "SNS00213276", "city": "徐州市", "county": "沛县", "alert_record_count": 30},
                        {"name": "SNS00204885", "city": "苏州市", "county": "昆山市", "alert_record_count": 30},
                        {"name": "SNS00213891", "city": "徐州市", "county": "睢宁县", "alert_record_count": 26},
                    ],
                },
                "must_surface_facts": ["徐州市沛县", "苏州市昆山市"],
            },
        )

        self.assertIn("徐州市沛县", text)
        self.assertIn("苏州市昆山市", text)
        self.assertIn("30 条", text)
        self.assertIn("26 条", text)

    def test_ranking_renderer_mentions_city_context_for_county_ranking(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_ranking",
            answer_evidence_profile={
                "entity_name": "全局",
                "display_focus": "normal",
                "severity_basis": "alert_record_count",
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "entity_resolution_trace": {"confidence_notice": ""},
                "derived_summary": {
                    "aggregation": "county",
                    "top_n": 2,
                    "severity_items": [
                        {"name": "睢宁县", "city": "徐州市", "county": "睢宁县", "alert_record_count": 39},
                        {"name": "昆山市", "city": "苏州市", "county": "昆山市", "alert_record_count": 37},
                    ],
                },
                "must_surface_facts": ["徐州市睢宁县", "苏州市昆山市"],
            },
        )

        self.assertIn("徐州市睢宁县", text)
        self.assertIn("苏州市昆山市", text)
        self.assertIn("39 条", text)
        self.assertIn("37 条", text)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for deterministic raw-only business answer rendering."""

from __future__ import annotations

import unittest

from app.services.business_answer_renderer import BusinessAnswerRenderer


class BusinessAnswerRendererTest(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = BusinessAnswerRenderer()

    def test_summary_renderer_mentions_absolute_window_and_raw_counts(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            result={
                "entity_name": "南通市",
                "total_records": 37,
                "avg_water20cm": 96.21,
                "device_count": 12,
                "region_count": 4,
                "latest_create_time": "2026-04-13 23:59:59",
                "top_regions": [{"region": "如东县"}, {"region": "海安市"}],
                "time_window": {
                    "start_time": "2026-04-13 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "output_mode": "normal",
            },
            resolved_args={
                "city": "南通市",
                "start_time": "2026-04-13 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("南通市", text)
        self.assertIn("2026-04-13", text)
        self.assertIn("37 条记录", text)
        self.assertIn("12 个点位", text)
        self.assertIn("如东县", text)

    def test_summary_renderer_appends_medium_confidence_notice(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            result={
                "entity_name": "海安市",
                "total_records": 65,
                "avg_water20cm": 109.56,
                "device_count": 8,
                "region_count": 1,
                "latest_create_time": "2026-04-13 23:59:59",
                "top_regions": [],
                "time_window": {
                    "start_time": "2026-04-01 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "output_mode": "normal",
            },
            resolved_args={
                "county": "海安市",
                "start_time": "2026-04-01 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="medium",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("海安市", text)
        self.assertIn("置信度中", text)

    def test_detail_renderer_mentions_inherited_time_and_full_region_context(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_detail",
            result={
                "entity_type": "device",
                "entity_name": "SNS00204333",
                "record_count": 7,
                "avg_water20cm": 93.10,
                "time_window": {
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "latest_record": {
                    "sn": "SNS00204333",
                    "city": "南通市",
                    "county": "如东县",
                    "create_time": "2026-04-13 23:59:17",
                    "water20cm": "92.43",
                },
                "output_mode": "normal",
            },
            resolved_args={
                "sn": "SNS00204333",
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="history_inherited",
            used_context=True,
            context_correction=False,
        )

        self.assertIn("沿用最近 7 天", text)
        self.assertIn("南通市如东县", text)
        self.assertIn("SNS00204333", text)

    def test_detail_renderer_mentions_correction_when_switching_entity(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_detail",
            result={
                "entity_type": "region",
                "entity_name": "如皋市",
                "record_count": 28,
                "avg_water20cm": 128.98,
                "time_window": {
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "latest_record": {
                    "sn": "SNS00215012",
                    "city": "南通市",
                    "county": "如皋市",
                    "create_time": "2026-04-13 23:59:17",
                    "water20cm": "128.98",
                },
                "output_mode": "normal",
            },
            resolved_args={
                "county": "如皋市",
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="history_inherited",
            used_context=True,
            context_correction=True,
        )

        self.assertIn("已切换到如皋市", text)
        self.assertIn("沿用最近 7 天", text)

    def test_comparison_renderer_mentions_both_entities_and_raw_counts(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_comparison",
            result={
                "entity_type": "region",
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "items": [
                    {"name": "睢宁县", "record_count": 210, "device_count": 11, "avg_water20cm": 132.61},
                    {"name": "沛县", "record_count": 240, "device_count": 13, "avg_water20cm": 112.62},
                ],
            },
            resolved_args={
                "start_time": "2026-03-15 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("睢宁县", text)
        self.assertIn("沛县", text)
        self.assertIn("210 条记录", text)
        self.assertIn("240 条记录", text)

    def test_ranking_renderer_mentions_device_region_context(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_ranking",
            result={
                "aggregation": "device",
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "items": [
                    {"name": "SNS00213276", "record_count": 30, "city": "徐州市", "county": "沛县"},
                    {"name": "SNS00204885", "record_count": 28, "city": "苏州市", "county": "昆山市"},
                    {"name": "SNS00213891", "record_count": 26, "city": "徐州市", "county": "睢宁县"},
                ],
            },
            resolved_args={
                "aggregation": "device",
                "start_time": "2026-03-15 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("徐州市沛县", text)
        self.assertIn("苏州市昆山市", text)
        self.assertIn("30 条", text)
        self.assertIn("26 条", text)


if __name__ == "__main__":
    unittest.main()

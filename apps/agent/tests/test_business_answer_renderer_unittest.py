"""Unit tests for deterministic business answer rendering."""

from __future__ import annotations

import unittest

from app.services.business_answer_renderer import BusinessAnswerRenderer


class BusinessAnswerRendererTest(unittest.TestCase):
    """Business answers should be rendered by program rules, not free-form LLM text."""

    def setUp(self) -> None:
        self.renderer = BusinessAnswerRenderer()

    def test_summary_renderer_mentions_absolute_window_and_overall_stability(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            result={
                "total_records": 37,
                "avg_water20cm": 96.21,
                "alert_count": 0,
                "status_counts": {"not_triggered": 37},
                "top_alert_regions": [],
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
        self.assertIn("总体平稳", text)

    def test_summary_renderer_appends_medium_confidence_notice(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            result={
                "total_records": 65,
                "avg_water20cm": 109.56,
                "alert_count": 0,
                "status_counts": {"not_triggered": 65},
                "top_alert_regions": [],
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
                    "soil_status": "not_triggered",
                },
                "alert_records": [],
                "status_summary": {"not_triggered": 7},
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
                    "soil_status": "waterlogging",
                },
                "alert_records": [
                    {
                        "sn": "SNS00215012",
                        "city": "南通市",
                        "county": "如皋市",
                        "create_time": "2026-04-13 23:59:17",
                        "water20cm": "128.98",
                        "soil_status": "waterlogging",
                    }
                ],
                "status_summary": {"not_triggered": 27, "waterlogging": 1},
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

    def test_comparison_renderer_mentions_winner_and_basis_counts(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_comparison",
            result={
                "entity_type": "region",
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "winner": "睢宁县",
                "winner_basis": "alert_count",
                "items": [
                    {"name": "睢宁县", "alert_count": 39, "avg_risk_score": 55.84, "avg_water20cm": 132.61, "record_count": 210},
                    {"name": "沛县", "alert_count": 36, "avg_risk_score": 59.6, "avg_water20cm": 112.62, "record_count": 240},
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
        self.assertIn("39", text)
        self.assertIn("36", text)

    def test_summary_renderer_mentions_top_regions_when_alerts_exist(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_summary",
            result={
                "entity_name": "全局",
                "total_records": 3689,
                "avg_water20cm": 93.77,
                "alert_count": 44,
                "status_counts": {"not_triggered": 3645, "waterlogging": 44},
                "top_alert_regions": [
                    {"region": "睢宁县", "alert_count": 9},
                    {"region": "沛县", "alert_count": 8},
                    {"region": "昆山市", "alert_count": 7},
                ],
                "time_window": {
                    "start_time": "2026-04-07 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "output_mode": "normal",
            },
            resolved_args={
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("睢宁县", text)
        self.assertIn("沛县", text)
        self.assertIn("昆山市", text)

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
                    {"name": "SNS00213276", "alert_count": 30, "city": "徐州市", "county": "沛县"},
                    {"name": "SNS00204885", "alert_count": 30, "city": "苏州市", "county": "昆山市"},
                    {"name": "SNS00213891", "alert_count": 26, "city": "徐州市", "county": "睢宁县"},
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
        self.assertIn("30", text)
        self.assertIn("26", text)

    def test_detail_anomaly_renderer_uses_total_alert_count_and_representative_device(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_detail",
            result={
                "entity_type": "region",
                "entity_name": "睢宁县",
                "record_count": 210,
                "alert_count": 39,
                "time_window": {
                    "start_time": "2026-03-15 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "latest_record": {
                    "sn": "SNS00213891",
                    "city": "徐州市",
                    "county": "睢宁县",
                    "create_time": "2026-04-13 23:59:17",
                    "water20cm": "141.38",
                    "soil_status": "not_triggered",
                },
                "alert_records": [
                    {
                        "sn": "SNS00213891",
                        "city": "徐州市",
                        "county": "睢宁县",
                        "create_time": "2026-04-13 23:59:17",
                        "water20cm": "159.34",
                        "soil_status": "waterlogging",
                    }
                ],
                "alert_period_summary": {
                    "start_time": "2026-03-15 23:59:17",
                    "end_time": "2026-04-09 23:59:17",
                    "alert_count": 39,
                    "representative_record": {
                        "sn": "SNS00213891",
                        "city": "徐州市",
                        "county": "睢宁县",
                        "create_time": "2026-04-09 23:59:17",
                        "water20cm": "159.34",
                        "soil_status": "waterlogging",
                    },
                },
                "status_summary": {"not_triggered": 171, "waterlogging": 39},
                "output_mode": "anomaly_focus",
            },
            resolved_args={
                "county": "睢宁县",
                "start_time": "2026-03-15 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="rule_relative",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("39", text)
        self.assertIn("SNS00213891", text)
        self.assertIn("涝渍", text)

    def test_detail_advice_renderer_mentions_historical_alert_period(self) -> None:
        text = self.renderer.render(
            tool_name="query_soil_detail",
            result={
                "entity_type": "device",
                "entity_name": "SNS00204334",
                "record_count": 103,
                "alert_count": 14,
                "time_window": {
                    "start_time": "2026-01-01 00:00:00",
                    "end_time": "2026-04-13 23:59:59",
                },
                "latest_record": {
                    "sn": "SNS00204334",
                    "city": "南通市",
                    "county": "如东县",
                    "create_time": "2026-04-13 23:59:17",
                    "water20cm": "92.43",
                    "soil_status": "not_triggered",
                },
                "alert_records": [
                    {
                        "sn": "SNS00204334",
                        "city": "南通市",
                        "county": "如东县",
                        "create_time": "2026-01-14 23:59:17",
                        "water20cm": "43.20",
                        "soil_status": "heavy_drought",
                    }
                ],
                "alert_period_summary": {
                    "start_time": "2026-01-10 23:59:17",
                    "end_time": "2026-01-14 23:59:17",
                    "alert_count": 14,
                    "representative_record": {
                        "sn": "SNS00204334",
                        "city": "南通市",
                        "county": "如东县",
                        "create_time": "2026-01-14 23:59:17",
                        "water20cm": "43.20",
                        "soil_status": "heavy_drought",
                    },
                },
                "status_summary": {"not_triggered": 89, "heavy_drought": 14},
                "output_mode": "advice_mode",
            },
            resolved_args={
                "sn": "SNS00204334",
                "output_mode": "advice_mode",
                "start_time": "2026-01-01 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            entity_confidence="high",
            time_source="default_current_year",
            used_context=False,
            context_correction=False,
        )

        self.assertIn("2026-01-10", text)
        self.assertIn("2026-01-14", text)
        self.assertIn("建议", text)


if __name__ == "__main__":
    unittest.main()

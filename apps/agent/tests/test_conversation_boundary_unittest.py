"""Unit tests for conversation boundary handling."""

from __future__ import annotations

import asyncio
import unittest

from app.services.conversation_boundary_service import ConversationBoundaryService


class ConversationBoundaryServiceTest(unittest.TestCase):
    """Test cases for multi-turn boundary decisions."""

    def setUp(self) -> None:
        self.service = ConversationBoundaryService()

    def test_follow_up_without_context_should_clarify_missing_context(self) -> None:
        result = self.service.decide(
            raw_slots={"follow_up": True},
            intent="soil_region_query",
            recent_context=[],
        )

        self.assertEqual(result["next_action"], "clarify_missing_context")
        self.assertEqual(result["inheritance_mode"], "clarify_missing_context")

    def test_region_switch_should_carry_compatible_frame(self) -> None:
        result = self.service.decide(
            raw_slots={"city_name": "徐州市"},
            intent="soil_region_query",
            recent_context=[
                {
                    "turn_id": 1,
                    "entity_context": {"city_name": "南京市"},
                    "query_frame": {"query_family": "anomaly", "intent": "soil_anomaly_query"},
                    "resolved_window": {
                        "start_time": "2026-03-15 00:00:00",
                        "end_time": "2026-04-13 23:59:59",
                        "time_label": "last_30_days",
                        "time_explicit": True,
                    },
                    "base_query_family": "anomaly",
                }
            ],
        )

        self.assertEqual(result["next_action"], "carry_frame")
        self.assertEqual(result["patch"]["intent"], "soil_anomaly_query")
        self.assertEqual(result["patch"]["answer_type"], "soil_anomaly_answer")
        self.assertEqual(result["patch"]["context_used"]["inheritance_mode"], "carry_frame")
        self.assertIn("city_name", result["patch"]["context_used"]["overridden_fields"])

    def test_ranking_to_device_should_convert_to_detail(self) -> None:
        result = self.service.decide(
            raw_slots={"device_sn": "SNS00204333"},
            intent="soil_region_query",
            recent_context=[
                {
                    "turn_id": 1,
                    "entity_context": {"county_name": "如东县"},
                    "query_frame": {"query_family": "ranking", "intent": "soil_severity_ranking"},
                    "resolved_window": {
                        "start_time": "2026-04-07 00:00:00",
                        "end_time": "2026-04-13 23:59:59",
                        "time_label": "last_7_days",
                        "time_explicit": False,
                    },
                    "base_query_family": "ranking",
                }
            ],
        )

        self.assertEqual(result["next_action"], "convert_frame")
        self.assertEqual(result["patch"]["intent"], "soil_device_query")
        self.assertEqual(result["patch"]["answer_type"], "soil_detail_answer")
        self.assertEqual(result["patch"]["context_used"]["inheritance_mode"], "convert_frame")


if __name__ == "__main__":
    unittest.main()

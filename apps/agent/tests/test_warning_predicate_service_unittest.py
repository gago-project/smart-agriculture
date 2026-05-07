from __future__ import annotations

import datetime as dt
import unittest


class WarningPredicateServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.warning_predicate_service import WarningPredicateService

        self.service = WarningPredicateService()
        self.rule_row = {
            "rule_code": "soil_warning_v1",
            "rule_definition_json": {
                "rules": [
                    {"warning_level": "device_fault", "condition": "water20cm = 0 and t20cm = 0", "priority": 5},
                    {"warning_level": "heavy_drought", "condition": "water20cm < 50", "priority": 10},
                    {"warning_level": "waterlogging", "condition": "water20cm >= 150", "priority": 20},
                ],
                "seasonal_overrides": [
                    {
                        "name": "夏季涝渍暂停",
                        "description": "每年6月1日至10月31日暂停涝渍预警",
                        "period": {"month_start": 6, "day_start": 1, "month_end": 10, "day_end": 31},
                        "suspended_warning_levels": ["waterlogging"],
                    }
                ],
            },
        }

    def test_build_sql_predicate_uses_rule_thresholds_and_record_time_override(self) -> None:
        predicate = self.service.build_sql_predicate(
            rule_row=self.rule_row,
            warning_type="waterlogging",
            time_column="create_time",
        )

        self.assertIn("water20cm >= 150", predicate)
        self.assertIn("create_time", predicate)
        self.assertIn("6", predicate)
        self.assertIn("10", predicate)

    def test_evaluate_respects_seasonal_override_for_each_record_time(self) -> None:
        july = self.service.evaluate(
            {"water20cm": 160, "t20cm": 21},
            self.rule_row,
            dt.datetime(2026, 7, 15, 12, 0, 0),
        )
        april = self.service.evaluate(
            {"water20cm": 160, "t20cm": 21},
            self.rule_row,
            dt.datetime(2026, 4, 15, 12, 0, 0),
        )

        self.assertFalse(july.matched)
        self.assertIsNone(july.warning_level)
        self.assertTrue(april.matched)
        self.assertEqual(april.warning_level, "waterlogging")

    def test_evaluate_keeps_device_fault_priority(self) -> None:
        result = self.service.evaluate(
            {"water20cm": 0, "t20cm": 0},
            self.rule_row,
            dt.datetime(2026, 8, 1, 8, 0, 0),
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.warning_level, "device_fault")


if __name__ == "__main__":
    unittest.main()

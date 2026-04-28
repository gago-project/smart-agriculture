from __future__ import annotations

import unittest

from app.services.time_window_service import TimeWindowService


class TimeWindowServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TimeWindowService()
        self.latest_business_time = "2026-04-13 23:59:17"

    def test_recent_n_days_expands_to_absolute_window(self) -> None:
        result = self.service.resolve("南京最近13天墒情怎么样", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.time_source, "rule_relative")
        self.assertEqual(result.start_time, "2026-04-01 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")

    def test_two_weeks_expands_as_rolling_days(self) -> None:
        result = self.service.resolve("海安市两周墒情", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertEqual(result.start_time, "2026-03-31 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")

    def test_three_months_expands_as_rolling_natural_months(self) -> None:
        result = self.service.resolve("南通最近3个月墒情", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertEqual(result.start_time, "2026-02-01 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")

    def test_absolute_date_keeps_time_signal_but_skips_rule_expansion(self) -> None:
        result = self.service.resolve("南京4月1日到4月10日墒情", self.latest_business_time)

        self.assertFalse(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertIsNone(result.start_time)
        self.assertIsNone(result.end_time)

    def test_ambiguous_time_phrase_requires_clarification(self) -> None:
        result = self.service.resolve("这几天南京墒情", self.latest_business_time)

        self.assertFalse(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.clarify_reason, "ambiguous_time")

    def test_no_time_signal_is_detected(self) -> None:
        result = self.service.resolve("南京墒情怎么样", self.latest_business_time)

        self.assertFalse(result.matched)
        self.assertFalse(result.has_time_signal)
        self.assertIsNone(result.start_time)
        self.assertIsNone(result.end_time)


if __name__ == "__main__":
    unittest.main()

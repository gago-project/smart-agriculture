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

    def test_bare_n_days_reply_expands_to_absolute_window(self) -> None:
        result = self.service.resolve("7天", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.time_source, "rule_relative")
        self.assertEqual(result.start_time, "2026-04-07 00:00:00")
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

    def test_bare_recent_defaults_to_recent_seven_days(self) -> None:
        result = self.service.resolve("最近墒情怎么样", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertEqual(result.start_time, "2026-04-07 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")

    def test_recent_one_month_expands_as_rolling_thirty_days(self) -> None:
        result = self.service.resolve("睢宁县最近一个月有没有异常", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertEqual(result.start_time, "2026-03-15 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")

    def test_absolute_year_month_with_spaces_expands_to_exact_month(self) -> None:
        result = self.service.resolve("查一下 SNS00204333 在 2025 年 1 月的墒情", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.start_time, "2025-01-01 00:00:00")
        self.assertEqual(result.end_time, "2025-01-31 23:59:59")

    def test_absolute_month_day_range_expands_with_anchor_year(self) -> None:
        result = self.service.resolve("南京4月1日到4月10日墒情", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.start_time, "2026-04-01 00:00:00")
        self.assertEqual(result.end_time, "2026-04-10 23:59:59")

    def test_single_absolute_day_with_four_digit_year_expands_to_one_day_window(self) -> None:
        result = self.service.resolve("2026年3月20日全省出现墒情预警信息的点位是哪些", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.time_source, "rule_absolute")
        self.assertEqual(result.start_time, "2026-03-20 00:00:00")
        self.assertEqual(result.end_time, "2026-03-20 23:59:59")

    def test_single_absolute_day_with_two_digit_year_and_hao_expands_to_one_day_window(self) -> None:
        result = self.service.resolve("26年3月20号全省出现墒情预警信息的点位是哪些", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertTrue(result.has_time_signal)
        self.assertEqual(result.time_source, "rule_absolute")
        self.assertEqual(result.start_time, "2026-03-20 00:00:00")
        self.assertEqual(result.end_time, "2026-03-20 23:59:59")

    def test_this_year_expands_from_year_start_to_anchor_day(self) -> None:
        result = self.service.resolve("南通市今年需要发预警吗", self.latest_business_time)

        self.assertTrue(result.matched)
        self.assertEqual(result.start_time, "2026-01-01 00:00:00")
        self.assertEqual(result.end_time, "2026-04-13 23:59:59")

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

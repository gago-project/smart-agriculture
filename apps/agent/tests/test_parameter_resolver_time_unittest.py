from __future__ import annotations

import unittest

from app.services.parameter_resolver_service import ParameterResolverService
from app.services.time_window_service import TimeWindowResolution


class ParameterResolverTimeContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_time_signal_requires_clarification(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {"city": "南京市"},
            latest_business_time="2026-04-13 23:59:17",
            user_input="南京墒情怎么样",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=False),
        )

        self.assertTrue(result.should_clarify)
        self.assertIn("时间段", result.clarify_message)

    async def test_rule_relative_time_overrides_conflicting_llm_window(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {
                "city": "南京市",
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            latest_business_time="2026-04-13 23:59:17",
            user_input="南京最近13天墒情怎么样",
            time_evidence=TimeWindowResolution(
                matched=True,
                has_time_signal=True,
                time_source="rule_relative",
                start_time="2026-04-01 00:00:00",
                end_time="2026-04-13 23:59:59",
            ),
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-04-01 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-13 23:59:59")
        self.assertTrue(any("冲突" in warning for warning in result.warning_trace))

    async def test_absolute_window_without_relative_match_is_accepted(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {
                "city": "南京市",
                "start_time": "2026-04-01 00:00:00",
                "end_time": "2026-04-10 23:59:59",
            },
            latest_business_time="2026-04-13 23:59:17",
            user_input="南京4月1日到4月10日墒情怎么样",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=True),
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-04-01 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-10 23:59:59")

    async def test_invalid_time_range_is_clarified(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {
                "city": "南京市",
                "start_time": "2026-04-13 00:00:00",
                "end_time": "2026-04-01 23:59:59",
            },
            latest_business_time="2026-04-13 23:59:17",
            user_input="南京4月13日到4月1日墒情怎么样",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=True),
        )

        self.assertTrue(result.should_clarify)
        self.assertIn("开始时间", result.clarify_message)


if __name__ == "__main__":
    unittest.main()

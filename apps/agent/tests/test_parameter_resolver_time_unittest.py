from __future__ import annotations

import unittest

from app.services.parameter_resolver_service import ParameterResolverService
from app.services.time_window_service import TimeWindowResolution


class ParameterResolverTimeContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_time_signal_without_entity_requires_clarification(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {},
            latest_business_time="2026-04-13 23:59:17",
            user_input="帮我查一下",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=False),
        )

        self.assertTrue(result.should_clarify)
        self.assertIn("时间段", result.clarify_message)

    async def test_missing_time_signal_defaults_region_summary_to_recent_7_days(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {"city": "南京市"},
            latest_business_time="2026-04-13 23:59:17",
            user_input="查一下南京的情况",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=False),
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-04-07 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result.time_source, "default_recent_7d")

    async def test_advice_mode_without_time_defaults_to_current_year(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_detail",
            {"sn": "SNS00204334", "output_mode": "advice_mode"},
            latest_business_time="2026-04-13 23:59:17",
            user_input="SNS00204334 这种情况需要注意什么",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=False),
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-01-01 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result.time_source, "default_current_year")

    async def test_default_time_window_overrides_llm_guessed_absolute_range_when_turn_has_no_time(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_summary",
            {
                "city": "南通市",
                "start_time": "2026-04-01 00:00:00",
                "end_time": "2026-04-13 23:59:17",
            },
            latest_business_time="2026-04-13 23:59:17",
            user_input="查一下南通的情况",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=False),
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-04-07 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result.time_source, "default_recent_7d")

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

    async def test_history_window_overrides_llm_absolute_guess_when_turn_has_no_new_time(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_detail",
            {
                "sn": "SNS00204333",
                "start_time": "2026-04-01 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
            latest_business_time="2026-04-13 23:59:17",
            user_input="那其中 SNS00204333 呢",
            time_evidence=TimeWindowResolution(matched=False, has_time_signal=False),
            inherited_time_window={
                "start_time": "2026-04-07 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-04-07 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result.time_source, "history_inherited")

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

    async def test_standalone_resolver_accepts_raw_absolute_window_without_time_evidence(self) -> None:
        resolver = ParameterResolverService()

        result = await resolver.resolve(
            "query_soil_detail",
            {
                "city": "南京市",
                "start_time": "2026-04-01 00:00:00",
                "end_time": "2026-04-10 23:59:59",
            },
            latest_business_time="2026-04-13 23:59:17",
            user_input="南京4月1日到4月10日墒情怎么样",
            time_evidence=None,
        )

        self.assertFalse(result.should_clarify)
        self.assertEqual(result.resolved_args["start_time"], "2026-04-01 00:00:00")
        self.assertEqual(result.resolved_args["end_time"], "2026-04-10 23:59:59")


if __name__ == "__main__":
    unittest.main()

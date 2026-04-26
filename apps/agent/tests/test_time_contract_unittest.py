"""Unit tests for the post-batch-removal time contract."""

from __future__ import annotations

import unittest

from app.services.execution_gate_service import ExecutionGateService
from app.services.intent_slot_service import IntentSlotService
from app.services.soil_query_service import SoilQueryService
from app.services.time_service import TimeResolveService
from support_repositories import SeedSoilRepository


LEGACY_BATCH_SLOT = "batch" + "_id"
LEGACY_BATCH_VALUE = "latest" + "_batch"


class FakeQwenBatchClient:
    """LLM test double that wrongly returns deprecated batch slots."""

    def available(self) -> bool:
        """Return whether this test double should be treated as available."""
        return True

    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        """Return a deprecated batch-style parse that should be sanitized."""
        del user_input, session_id
        return {
            "intent": "soil_recent_summary",
            "answer_type": "soil_summary_answer",
            "slots": {
                "time_range": "last_7_days",
                LEGACY_BATCH_SLOT: LEGACY_BATCH_VALUE,
            },
        }


class TimeContractTest(unittest.TestCase):
    """Test the simplified time-window contract after batch removal."""

    def setUp(self) -> None:
        """Prepare shared services for each test."""
        self.repository = SeedSoilRepository()
        self.time_service = TimeResolveService(self.repository)
        self.query_service = SoilQueryService(self.repository)
        self.execution_gate = ExecutionGateService()

    def test_yesterday_should_resolve_to_full_previous_business_day(self) -> None:
        """Verify yesterday maps to the previous natural day boundaries."""
        result = self.time_service.resolve(
            slots={"time_range": "yesterday"},
            latest_business_time="2026-04-13 23:59:17",
        )

        self.assertEqual(result["start_time"], "2026-04-12 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-12 23:59:59")
        self.assertEqual(result["resolved_time_range"], "yesterday")

    def test_last_12_days_should_resolve_to_natural_day_window(self) -> None:
        """Verify dynamic day windows use inclusive natural-day boundaries."""
        result = self.time_service.resolve(
            slots={"time_range": "last_12_days"},
            latest_business_time="2026-04-13 23:59:17",
        )

        self.assertEqual(result["start_time"], "2026-04-02 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result["resolved_time_range"], "last_12_days")

    def test_last_week_should_resolve_to_previous_natural_week(self) -> None:
        """Verify last week maps to Monday-Sunday boundaries."""
        result = self.time_service.resolve(
            slots={"time_range": "last_week"},
            latest_business_time="2026-04-13 23:59:17",
        )

        self.assertEqual(result["start_time"], "2026-04-06 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-12 23:59:59")

    def test_dynamic_last_n_days_should_fetch_latest_business_time(self) -> None:
        """Verify dynamic day windows still fetch latest business time from repo."""
        result = self.query_service.build_query_plan(
            intent="soil_recent_summary",
            slots={"city": "南京市", "time_range": "last_12_days"},
            business_time=self.time_service.resolve(
                slots={"city": "南京市", "time_range": "last_12_days"},
                latest_business_time=self.repository.latest_business_time(),
            ),
            session_id="s1",
            turn_id=1,
            request_id="r1",
        )

        self.assertEqual(set(result["filters"].keys()), {"city", "county", "sn"})
        self.assertEqual(result["time_range"]["start_time"], "2026-04-02 00:00:00")
        self.assertEqual(result["time_range"]["end_time"], "2026-04-13 23:59:59")

    def test_execution_gate_should_use_resolved_day_span_instead_of_time_label_map(self) -> None:
        """Verify gate limits are driven by start/end time, not a fixed label map."""
        result = self.execution_gate.evaluate(
            intent="soil_anomaly_query",
            slots={"time_range": "last_181_days"},
            business_time={
                "resolved_time_range": "last_181_days",
                "start_time": "2025-10-15 00:00:00",
                "end_time": "2026-04-13 23:59:59",
            },
        )

        self.assertEqual(result["decision"], "clarify")
        self.assertNotIn("requested_days", result)
        self.assertNotIn("resolved_days", result)

    def test_missing_explicit_time_should_not_be_filled_in_intent_slot_stage(self) -> None:
        """Verify intent parsing keeps time empty until resolve stage."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("南京墒情怎么样", "no-explicit-time")
            self.assertNotIn("time_range", result.slots)
            self.assertEqual(result.answer_type, "soil_summary_answer")

        asyncio.run(run_case())

    def test_inherited_absolute_window_should_be_preserved(self) -> None:
        """Verify inherited resolved window is used directly without drift."""
        result = self.time_service.resolve(
            slots={"time_range": "last_7_days"},
            latest_business_time="2026-04-13 23:59:17",
            inherited_window={
                "start_time": "2026-04-01 00:00:00",
                "end_time": "2026-04-07 23:59:59",
                "time_label": "last_week",
                "time_explicit": True,
            },
            inherit_resolved_window=True,
        )

        self.assertEqual(result["start_time"], "2026-04-01 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-07 23:59:59")
        self.assertEqual(result["resolved_time_range"], "last_week")

    def test_qwen_batch_slots_should_be_sanitized(self) -> None:
        """Verify deprecated batch slots from Qwen are dropped."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=FakeQwenBatchClient())
            result = await service.parse("帮我看一下", "llm-batch")
            self.assertEqual(result.intent, "soil_recent_summary")
            self.assertEqual(result.answer_type, "soil_summary_answer")
            self.assertEqual(result.slots.get("time_range"), "last_7_days")
            self.assertNotIn(LEGACY_BATCH_SLOT, result.slots)

        asyncio.run(run_case())

    def test_anchor_before_phrase_should_not_produce_top_n(self) -> None:
        """Verify '之前50天' is not misread as top_n=50."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("2025-12-01之前50天的哪些设备最严重", "fix-top-n")
            self.assertNotIn("top_n", result.slots)

        asyncio.run(run_case())

    def test_explicit_top_n_still_works_after_fix(self) -> None:
        """Verify 前5 still produces top_n=5 after the lookbehind fix."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("过去一个月前5个最严重的设备", "fix-top-n-ok")
            self.assertEqual(result.slots.get("top_n"), 5)

        asyncio.run(run_case())

    def test_relative_anchor_phrase_should_not_produce_top_n(self) -> None:
        """Verify '7天前的前7天' does not produce a top_n slot."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("7天前的前7天的情况", "fix-relative-top-n")
            self.assertNotIn("top_n", result.slots)

        asyncio.run(run_case())

    def test_anchor_before_should_parse_to_correct_time_range_and_target_date(self) -> None:
        """Verify '2025-12-01之前50天' sets time_range and target_date correctly."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("2025-12-01之前50天的哪些设备最严重", "anchor-before")
            self.assertEqual(result.slots.get("time_range"), "anchor_before_50_days")
            self.assertEqual(result.slots.get("target_date"), "2025-12-01")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_anchor_after_should_parse_to_correct_time_range_and_target_date(self) -> None:
        """Verify '2025-12-01之后30天' sets time_range and target_date correctly."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("2025-12-01之后30天整体墒情怎么样", "anchor-after")
            self.assertEqual(result.slots.get("time_range"), "anchor_after_30_days")
            self.assertEqual(result.slots.get("target_date"), "2025-12-01")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_plain_iso_date_still_resolves_as_exact_date(self) -> None:
        """Verify bare YYYY-MM-DD with no direction still gives exact_date."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("2025-12-01如东县墒情", "exact-date")
            self.assertEqual(result.slots.get("time_range"), "exact_date")
            self.assertEqual(result.slots.get("target_date"), "2025-12-01")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_anchor_before_50_days_should_resolve_to_correct_window(self) -> None:
        """Verify anchor_before_50_days ending on 2025-12-01 gives correct boundaries.

        Dec 1 inclusive, counting back 50 calendar days:
        Oct 13 (day 1) ... Dec 1 (day 50) — 19 Oct days + 30 Nov days + 1 Dec day = 50.
        """
        result = self.time_service.resolve(
            slots={"time_range": "anchor_before_50_days", "target_date": "2025-12-01"},
        )
        self.assertEqual(result["start_time"], "2025-10-13 00:00:00")
        self.assertEqual(result["end_time"], "2025-12-01 23:59:59")
        self.assertEqual(result["resolved_time_range"], "anchor_before_50_days")
        self.assertEqual(result["resolution_mode"], "anchor_window")
        self.assertEqual(result["time_basis"], "anchor_date")

    def test_anchor_after_30_days_should_resolve_to_correct_window(self) -> None:
        """Verify anchor_after_30_days starting on 2025-12-01 gives correct boundaries.

        Dec 1 inclusive, counting forward 30 calendar days:
        Dec 1 (day 1) ... Dec 30 (day 30).
        """
        result = self.time_service.resolve(
            slots={"time_range": "anchor_after_30_days", "target_date": "2025-12-01"},
        )
        self.assertEqual(result["start_time"], "2025-12-01 00:00:00")
        self.assertEqual(result["end_time"], "2025-12-30 23:59:59")
        self.assertEqual(result["resolved_time_range"], "anchor_after_30_days")
        self.assertEqual(result["resolution_mode"], "anchor_window")
        self.assertEqual(result["time_basis"], "anchor_date")

    def test_anchor_window_does_not_need_latest_business_time_fetch(self) -> None:
        """Verify anchor ranges skip the latest_business_time DB query."""
        import asyncio

        async def run_case() -> None:
            result = await self.query_service.fetch_latest_business_time_if_needed(
                slots={"time_range": "anchor_before_50_days", "target_date": "2025-12-01"},
                intent="soil_severity_ranking",
            )
            self.assertIsNone(result)

        asyncio.run(run_case())


    def test_n_days_ago_should_parse_to_label(self) -> None:
        """Verify '3天前的情况' sets time_range=n_days_ago_3 with time_explicit."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("3天前的情况", "n-days-ago")
            self.assertEqual(result.slots.get("time_range"), "n_days_ago_3")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_relative_anchor_before_should_parse_to_label(self) -> None:
        """Verify '7天前的前7天' sets time_range=relative_before_7_at_7_ago with time_explicit."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("7天前的前7天的情况", "relative-anchor")
            self.assertEqual(result.slots.get("time_range"), "relative_before_7_at_7_ago")
            self.assertTrue(result.slots.get("time_explicit"))
            self.assertNotIn("top_n", result.slots)

        asyncio.run(run_case())


    def test_n_days_ago_3_should_resolve_to_single_day(self) -> None:
        """Verify n_days_ago_3 resolves to the full day 3 days before latest_business_time."""
        result = self.time_service.resolve(
            slots={"time_range": "n_days_ago_3"},
            latest_business_time="2026-04-13 23:59:17",
        )
        self.assertEqual(result["start_time"], "2026-04-10 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-10 23:59:59")
        self.assertEqual(result["resolved_time_range"], "n_days_ago_3")
        self.assertEqual(result["resolution_mode"], "relative_window")

    def test_relative_before_7_at_7_ago_should_resolve_to_correct_window(self) -> None:
        """Verify relative_before_7_at_7_ago gives the 7-day window ending 7 days ago.

        Latest=Apr 13. Anchor=Apr 6 (7 days ago). 7-day window ending Apr 6:
        Mar 31 (day 1) ... Apr 6 (day 7).
        """
        result = self.time_service.resolve(
            slots={"time_range": "relative_before_7_at_7_ago"},
            latest_business_time="2026-04-13 23:59:17",
        )
        self.assertEqual(result["start_time"], "2026-03-31 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-06 23:59:59")
        self.assertEqual(result["resolved_time_range"], "relative_before_7_at_7_ago")
        self.assertEqual(result["resolution_mode"], "relative_window")


    def test_last_calendar_month_should_parse_to_label(self) -> None:
        """Verify '上个月的墒情' produces time_range=last_calendar_month."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("上个月的墒情", "last-cal-month")
            self.assertEqual(result.slots.get("time_range"), "last_calendar_month")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_current_calendar_month_should_parse_to_label(self) -> None:
        """Verify '本月的情况' produces time_range=current_calendar_month."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("本月的情况", "cur-cal-month")
            self.assertEqual(result.slots.get("time_range"), "current_calendar_month")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_current_week_should_parse_to_label(self) -> None:
        """Verify '本周异常' produces time_range=current_week."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("本周异常", "cur-week")
            self.assertEqual(result.slots.get("time_range"), "current_week")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())

    def test_n_weeks_should_fold_to_days_label(self) -> None:
        """Verify '过去3周' folds to time_range=last_21_days."""
        import asyncio

        async def run_case() -> None:
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            result = await service.parse("过去3周的墒情", "n-weeks")
            self.assertEqual(result.slots.get("time_range"), "last_21_days")
            self.assertTrue(result.slots.get("time_explicit"))

        asyncio.run(run_case())


    def test_last_calendar_month_should_resolve_to_march_2026(self) -> None:
        """Verify last_calendar_month from April 2026 gives all of March 2026."""
        result = self.time_service.resolve(
            slots={"time_range": "last_calendar_month"},
            latest_business_time="2026-04-13 23:59:17",
        )
        self.assertEqual(result["start_time"], "2026-03-01 00:00:00")
        self.assertEqual(result["end_time"], "2026-03-31 23:59:59")
        self.assertEqual(result["resolved_time_range"], "last_calendar_month")
        self.assertEqual(result["resolution_mode"], "relative_window")

    def test_current_calendar_month_should_resolve_to_april_2026(self) -> None:
        """Verify current_calendar_month from Apr 13 gives Apr 1 to Apr 13."""
        result = self.time_service.resolve(
            slots={"time_range": "current_calendar_month"},
            latest_business_time="2026-04-13 23:59:17",
        )
        self.assertEqual(result["start_time"], "2026-04-01 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result["resolved_time_range"], "current_calendar_month")
        self.assertEqual(result["resolution_mode"], "relative_window")

    def test_current_week_should_resolve_to_monday_only(self) -> None:
        """Verify current_week from Monday Apr 13 gives Apr 13 only (Mon=day 1)."""
        result = self.time_service.resolve(
            slots={"time_range": "current_week"},
            latest_business_time="2026-04-13 23:59:17",
        )
        self.assertEqual(result["start_time"], "2026-04-13 00:00:00")
        self.assertEqual(result["end_time"], "2026-04-13 23:59:59")
        self.assertEqual(result["resolved_time_range"], "current_week")
        self.assertEqual(result["resolution_mode"], "relative_window")


if __name__ == "__main__":
    unittest.main()

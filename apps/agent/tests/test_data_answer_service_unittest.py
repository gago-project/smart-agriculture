"""Unit tests for the server-backed deterministic data answer service."""

from __future__ import annotations

import unittest

from tests.support_repositories import SeedSoilRepository


class FakeLlmInputGuard:
    def __init__(self, intercepted_inputs: set[str] | None = None) -> None:
        self.intercepted_inputs = intercepted_inputs or set()
        self.calls: list[str] = []

    async def classify(self, text: str):
        from app.services.llm_input_guard_service import LlmInputGuardResult

        self.calls.append(text)
        if text in self.intercepted_inputs:
            return LlmInputGuardResult(decision="intercept", reason="noise", confidence=0.95)
        return LlmInputGuardResult(decision="allow", reason="noise", confidence=0.0)


class FakeLlmFollowUpResolver:
    def __init__(self, result=None) -> None:
        self.result = result
        self.calls: list[str] = []

    async def resolve(self, *, text: str, context: dict, latest_target: dict | None):
        del context, latest_target
        self.calls.append(text)
        return self.result


class DataAnswerServiceTest(unittest.IsolatedAsyncioTestCase):
    """Verify summary/list follow-up and topic isolation behavior."""

    async def asyncSetUp(self) -> None:
        from app.services.data_answer_service import DataAnswerService

        repository = SeedSoilRepository()
        repository.extra_region_aliases = [
            {
                "alias_name": "江苏",
                "canonical_name": "江苏省",
                "region_level": "province",
                "parent_city_name": None,
                "alias_source": "seed",
            },
            {
                "alias_name": "南京",
                "canonical_name": "南京市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "seed",
            },
            {
                "alias_name": "南京市",
                "canonical_name": "南京市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "canonical",
            },
            {
                "alias_name": "南通",
                "canonical_name": "南通市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "seed",
            },
            {
                "alias_name": "南通市",
                "canonical_name": "南通市",
                "region_level": "city",
                "parent_city_name": None,
                "alias_source": "canonical",
            },
            {
                "alias_name": "如东",
                "canonical_name": "如东县",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "seed",
            },
            {
                "alias_name": "如东县",
                "canonical_name": "如东县",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "canonical",
            },
            {
                "alias_name": "如皋",
                "canonical_name": "如皋市",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "seed",
            },
            {
                "alias_name": "如皋市",
                "canonical_name": "如皋市",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "canonical",
            },
            {
                "alias_name": "海安",
                "canonical_name": "海安市",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "seed",
            },
            {
                "alias_name": "海安市",
                "canonical_name": "海安市",
                "region_level": "county",
                "parent_city_name": "南通市",
                "alias_source": "canonical",
            },
        ]
        self.guard = FakeLlmInputGuard(
            intercepted_inputs={"上岛咖啡京东卡", "京东卡可以提现吗", "今天午饭吃什么"}
        )
        self.follow_up_guard = FakeLlmFollowUpResolver()
        self.repository = repository
        self.service = DataAnswerService(
            repository=repository,
            llm_input_guard=self.guard,
            llm_follow_up_resolver=self.follow_up_guard,
        )

    async def test_summary_then_list_follow_up_uses_focus_snapshot(self) -> None:
        summary = await self.service.reply(
            message="最近7天整体墒情怎么样",
            session_id="summary-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(summary["answer_kind"], "business")
        self.assertEqual(summary["capability"], "summary")
        self.assertEqual(summary["turn_context"]["context_version"], 3)
        self.assertEqual(summary["blocks"][0]["block_type"], "summary_card")
        self.assertEqual(summary["blocks"][0]["display_mode"], "evidence_only")
        self.assertTrue(summary["query_ref"]["has_query"])
        metrics = summary["blocks"][0]["metrics"]
        self.assertIn("record_count", metrics)
        self.assertIn("device_count", metrics)
        self.assertIn("region_count", metrics)
        self.assertIn("latest_create_time", metrics)
        for banned_key in ("risk_score", "display_label", "soil_status", "warning_level", "alert_record_count", "alert_device_count", "alert_region_count"):
            self.assertNotIn(banned_key, metrics)
        self.assertTrue(summary["turn_context"]["derived_sets"]["device_snapshot_id"])
        self.assertEqual(len(summary["turn_context"]["action_targets"]), 3)

        focus_snapshot_id = summary["turn_context"]["derived_sets"]["device_snapshot_id"]
        listing = await self.service.reply(
            message=f"{metrics['device_count']}个点位详情",
            session_id="summary-list",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertNotIn("display_mode", listing["blocks"][0])
        self.assertEqual(listing["blocks"][0]["pagination"]["snapshot_id"], focus_snapshot_id)
        self.assertEqual(listing["blocks"][0]["pagination"]["page_size"], 10)
        self.assertLessEqual(len(listing["blocks"][0]["rows"]), 10)
        self.assertGreaterEqual(listing["blocks"][0]["pagination"]["total_count"], 0)
        self.assertIn("点位", listing["blocks"][0]["title"])
        for row in listing["blocks"][0]["rows"]:
            self.assertIn("create_time", row)
            for banned_key in ("latest_create_time", "entity_key", "risk_score", "display_label", "soil_status", "warning_level"):
                self.assertNotIn(banned_key, row)

    async def test_detail_block_is_kept_for_evidence_but_marked_hidden_in_chat(self) -> None:
        detail = await self.service.reply(
            message="如东县详情",
            session_id="detail-hidden-block",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(detail["answer_kind"], "business")
        self.assertEqual(detail["capability"], "detail")
        self.assertEqual(detail["blocks"][0]["block_type"], "detail_card")
        self.assertEqual(detail["blocks"][0]["display_mode"], "evidence_only")
        self.assertEqual(detail["turn_context"]["query_state"]["query_profile"]["answer_mode"], "detail")
        latest_record = detail["blocks"][0]["latest_record"]
        for banned_key in ("risk_score", "display_label", "soil_status", "warning_level"):
            self.assertNotIn(banned_key, latest_record)

    async def test_summary_then_alert_record_follow_up_returns_record_list(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="summary-record-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        record_count = summary["blocks"][0]["metrics"]["record_count"]

        listing = await self.service.reply(
            message=f"这{record_count}条记录详情",
            session_id="summary-record-list",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertIn("记录", listing["blocks"][0]["title"])
        self.assertEqual(listing["blocks"][0]["pagination"]["page_size"], 10)
        self.assertLessEqual(len(listing["blocks"][0]["rows"]), 10)
        self.assertEqual(listing["blocks"][0]["pagination"]["total_count"], record_count)
        self.assertGreater(len(listing["blocks"][0]["rows"]), 1)

    async def test_record_list_follow_up_can_group_covered_regions(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="summary-region-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        record_count = summary["blocks"][0]["metrics"]["record_count"]
        region_count = summary["blocks"][0]["metrics"]["region_count"]

        listing = await self.service.reply(
            message=f"列出{record_count}条记录详情",
            session_id="summary-region-group",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        grouped = await self.service.reply(
            message=f"覆盖哪{region_count}个地区",
            session_id="summary-region-group",
            turn_id=3,
            current_context=listing["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertNotIn("display_mode", grouped["blocks"][0])
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")
        self.assertEqual(grouped["blocks"][0]["pagination"]["page_size"], 10)
        self.assertEqual(grouped["blocks"][0]["pagination"]["total_count"], region_count)
        self.assertLessEqual(len(grouped["blocks"][0]["rows"]), 10)
        self.assertEqual(grouped["blocks"][0]["columns"], ["city", "county"])
        for row in grouped["blocks"][0]["rows"]:
            self.assertIn("city", row)
            self.assertIn("county", row)
            for banned_key in ("group_key", "record_count", "device_count", "avg_water20cm", "latest_create_time", "max_risk_score"):
                self.assertNotIn(banned_key, row)
        self.assertIn("地区", grouped["final_text"])
        self.assertNotIn("当前整体墒情", grouped["final_text"])

    async def test_focus_device_follow_up_can_switch_back_to_alert_record_list(self) -> None:
        clarify = await self.service.reply(
            message="江苏最新的墒情情况",
            session_id="device-list-back-to-record-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        summary = await self.service.reply(
            message="1个月",
            session_id="device-list-back-to-record-list",
            turn_id=2,
            current_context=clarify["turn_context"],
            timezone="Asia/Shanghai",
        )
        region_count = summary["blocks"][0]["metrics"]["region_count"]
        device_count = summary["blocks"][0]["metrics"]["device_count"]
        record_count = summary["blocks"][0]["metrics"]["record_count"]

        grouped = await self.service.reply(
            message=f"哪{region_count}个地区",
            session_id="device-list-back-to-record-list",
            turn_id=3,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        focus_devices = await self.service.reply(
            message=f"{device_count}个点位是哪些",
            session_id="device-list-back-to-record-list",
            turn_id=4,
            current_context=grouped["turn_context"],
            timezone="Asia/Shanghai",
        )

        alert_records = await self.service.reply(
            message=f"{record_count}条记录详情",
            session_id="device-list-back-to-record-list",
            turn_id=5,
            current_context=focus_devices["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(alert_records["answer_kind"], "business")
        self.assertEqual(alert_records["capability"], "list")
        self.assertEqual(alert_records["blocks"][0]["block_type"], "list_table")
        self.assertIn("记录", alert_records["blocks"][0]["title"])
        self.assertEqual(alert_records["blocks"][0]["pagination"]["total_count"], record_count)

    async def test_focus_device_follow_up_can_group_regions_with_short_region_question(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="focus-device-short-region-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        device_count = summary["blocks"][0]["metrics"]["device_count"]
        region_count = summary["blocks"][0]["metrics"]["region_count"]

        focus_devices = await self.service.reply(
            message=f"{device_count}个点位详情",
            session_id="focus-device-short-region-group",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        grouped = await self.service.reply(
            message=f"{region_count}个地区呢",
            session_id="focus-device-short-region-group",
            turn_id=3,
            current_context=focus_devices["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")
        self.assertEqual(grouped["blocks"][0]["pagination"]["page_size"], 10)
        self.assertEqual(grouped["blocks"][0]["pagination"]["total_count"], region_count)
        self.assertLessEqual(len(grouped["blocks"][0]["rows"]), 10)

    async def test_record_list_follow_up_can_switch_to_involved_device_list(self) -> None:
        summary = await self.service.reply(
            message="如东县最近怎么样",
            session_id="record-list-to-device-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        record_count = summary["blocks"][0]["metrics"]["record_count"]
        device_count = summary["blocks"][0]["metrics"]["device_count"]

        record_list = await self.service.reply(
            message=f"{record_count}条数据给我一下",
            session_id="record-list-to-device-list",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="涉及的点位数据呢",
            session_id="record-list-to-device-list",
            turn_id=3,
            current_context=record_list["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "list")
        self.assertEqual(follow_up["blocks"][0]["block_type"], "list_table")
        self.assertIn("点位", follow_up["blocks"][0]["title"])
        self.assertEqual(follow_up["blocks"][0]["pagination"]["total_count"], device_count)

    async def test_focus_device_follow_up_treats_region_detail_phrase_as_group_request(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="focus-device-region-detail-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        device_count = summary["blocks"][0]["metrics"]["device_count"]
        region_count = summary["blocks"][0]["metrics"]["region_count"]

        focus_devices = await self.service.reply(
            message=f"{device_count}个点位详情",
            session_id="focus-device-region-detail-group",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        grouped = await self.service.reply(
            message=f"{region_count}个地区详情",
            session_id="focus-device-region-detail-group",
            turn_id=3,
            current_context=focus_devices["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")

    async def test_summary_follow_up_supports_place_alias_for_region_group(self) -> None:
        summary = await self.service.reply(
            message="最近墒情怎么样",
            session_id="summary-place-alias-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        grouped = await self.service.reply(
            message="这些地方呢",
            session_id="summary-place-alias-group",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")

    async def test_standalone_warning_device_query_returns_device_list_without_prior_context(self) -> None:
        listing = await self.service.reply(
            message="3月20号全省出现墒情预警信息的点位是哪些",
            session_id="standalone-warning-device-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertIn("点位", listing["blocks"][0]["title"])
        self.assertEqual(listing["turn_context"]["time_window"]["start_time"], "2026-03-20 00:00:00")
        self.assertEqual(listing["turn_context"]["time_window"]["end_time"], "2026-03-20 23:59:59")
        self.assertEqual(listing["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertGreater(len(listing["blocks"][0]["rows"]), 0)
        self.assertTrue(all(str(row.get("create_time") or "").startswith("2026-03-20") for row in listing["blocks"][0]["rows"]))
        from app.services.warning_predicate_service import WarningPredicateService

        warning_rows = WarningPredicateService().filter_records(
            self.repository.filter_records(
                start_time="2026-03-20 00:00:00",
                end_time="2026-03-20 23:59:59",
            ),
            self.repository.warning_rule_row(),
        )
        expected_devices = {str(row.get("sn") or "") for row in warning_rows if str(row.get("sn") or "")}
        returned_devices = {str(row.get("sn") or "") for row in listing["blocks"][0]["rows"] if str(row.get("sn") or "")}
        self.assertEqual(listing["blocks"][0]["pagination"]["total_count"], len(expected_devices))
        self.assertTrue(returned_devices.issubset(expected_devices))

    async def test_explicit_warning_device_query_is_not_captured_by_previous_follow_up_context(self) -> None:
        summary = await self.service.reply(
            message="最近7天整体墒情怎么样",
            session_id="fresh-warning-device-list-after-summary",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        listing = await self.service.reply(
            message="3月20号全省出现墒情预警信息的点位是哪些",
            session_id="fresh-warning-device-list-after-summary",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertIn("点位", listing["blocks"][0]["title"])
        self.assertEqual(listing["turn_context"]["time_window"]["start_time"], "2026-03-20 00:00:00")
        self.assertEqual(listing["turn_context"]["time_window"]["end_time"], "2026-03-20 23:59:59")
        self.assertNotIn("当前这轮可继续展开的是", listing["final_text"])
        self.assertGreater(len(listing["blocks"][0]["rows"]), 0)

    async def test_standalone_group_query_runs_without_prior_context(self) -> None:
        grouped = await self.service.reply(
            message="最近30天按地区汇总墒情数据",
            session_id="standalone-region-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")
        self.assertEqual(grouped["blocks"][0]["pagination"]["page_size"], 10)
        self.assertGreater(grouped["blocks"][0]["pagination"]["total_count"], 0)
        self.assertLessEqual(len(grouped["blocks"][0]["rows"]), 10)
        self.assertNotIn("请先查询一轮墒情数据", grouped["final_text"])

    async def test_standalone_group_query_supports_where_has_soil_data_wording(self) -> None:
        grouped = await self.service.reply(
            message="2026-04-13 有哪些地方有墒情数据",
            session_id="standalone-place-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")
        self.assertEqual(grouped["blocks"][0]["pagination"]["page_size"], 10)
        self.assertGreater(grouped["blocks"][0]["pagination"]["total_count"], 0)
        self.assertLessEqual(len(grouped["blocks"][0]["rows"]), 10)
        self.assertEqual(grouped["turn_context"]["time_window"]["start_time"], "2026-04-13 00:00:00")
        self.assertEqual(grouped["turn_context"]["time_window"]["end_time"], "2026-04-13 23:59:59")

    async def test_standalone_group_query_tolerates_colloquial_place_typo(self) -> None:
        grouped = await self.service.reply(
            message="2026-04-13 又哪些地方有墒情数据",
            session_id="standalone-place-group-typo",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(grouped["answer_kind"], "business")
        self.assertEqual(grouped["capability"], "group")
        self.assertEqual(grouped["blocks"][0]["block_type"], "group_table")
        self.assertEqual(grouped["blocks"][0]["group_by"], "region")
        self.assertEqual(grouped["blocks"][0]["pagination"]["page_size"], 10)
        self.assertGreater(grouped["blocks"][0]["pagination"]["total_count"], 0)
        self.assertLessEqual(len(grouped["blocks"][0]["rows"]), 10)
        self.assertEqual(grouped["turn_context"]["time_window"]["start_time"], "2026-04-13 00:00:00")
        self.assertEqual(grouped["turn_context"]["time_window"]["end_time"], "2026-04-13 23:59:59")

    async def test_warning_ranking_query_returns_group_result_instead_of_guidance(self) -> None:
        reply = await self.service.reply(
            message="最近30天，哪些地区墒情异常最多？",
            session_id="unsupported-derived-ranking",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "group")
        self.assertEqual(reply["blocks"][0]["block_type"], "group_table")
        self.assertEqual(reply["blocks"][0]["group_by"], "region")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertIn("徐州市睢宁县", reply["final_text"])

    async def test_summary_follow_up_supports_alert_record_alias_expand(self) -> None:
        summary = await self.service.reply(
            message="最近墒情怎么样",
            session_id="summary-record-alias-expand",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        record_count = summary["blocks"][0]["metrics"]["record_count"]

        listing = await self.service.reply(
            message=f"{record_count}条异常记录",
            session_id="summary-record-alias-expand",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertIn("记录", listing["blocks"][0]["title"])

    async def test_summary_follow_up_clarifies_when_region_count_does_not_match(self) -> None:
        summary = await self.service.reply(
            message="最近墒情怎么样",
            session_id="summary-region-count-mismatch",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        region_count = int(summary["blocks"][0]["metrics"]["region_count"])

        reply = await self.service.reply(
            message=f"{max(1, region_count - 1)}个地区详情",
            session_id="summary-region-count-mismatch",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "clarification")
        self.assertIn(str(region_count), reply["final_text"])

    async def test_summary_follow_up_stale_action_target_requires_clarification(self) -> None:
        summary = await self.service.reply(
            message="最近墒情怎么样",
            session_id="summary-stale-action-target",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        stale_context = {
            **summary["turn_context"],
            "action_targets": [
                {
                    **target,
                    "last_active_turn_id": 1,
                }
                for target in summary["turn_context"]["action_targets"]
            ],
        }

        reply = await self.service.reply(
            message="13个地区详情",
            session_id="summary-stale-action-target",
            turn_id=8,
            current_context=stale_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "clarification")
        self.assertIn("过期", reply["final_text"])

    async def test_group_follow_up_region_detail_keeps_time_window_detail_instead_of_latest_only(self) -> None:
        self.repository.extra_region_aliases.extend(
            [
                {
                    "alias_name": "仪征",
                    "canonical_name": "仪征市",
                    "region_level": "county",
                    "parent_city_name": "扬州市",
                    "alias_source": "seed",
                },
                {
                    "alias_name": "仪征市",
                    "canonical_name": "仪征市",
                    "region_level": "county",
                    "parent_city_name": "扬州市",
                    "alias_source": "canonical",
                },
            ]
        )
        summary = await self.service.reply(
            message="江苏上周墒情情况",
            session_id="group-region-detail-window",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        grouped = await self.service.reply(
            message=f"{summary['blocks'][0]['metrics']['region_count']}个地区详情",
            session_id="group-region-detail-window",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        detail = await self.service.reply(
            message="仪征详情",
            session_id="group-region-detail-window",
            turn_id=3,
            current_context=grouped["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(detail["answer_kind"], "business")
        self.assertEqual(detail["capability"], "detail")
        self.assertEqual(detail["blocks"][0]["block_type"], "detail_card")
        self.assertIn("仪征市2026-04-06至2026-04-12", detail["final_text"])
        self.assertNotIn("最新详情如下", detail["final_text"])
        self.assertNotIn("最近一条记录时间为", detail["final_text"])

    async def test_summary_result_ref_detail_still_beats_action_target_expand(self) -> None:
        summary = await self.service.reply(
            message="最近墒情怎么样",
            session_id="summary-result-ref-detail-priority",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        detail = await self.service.reply(
            message="第一个地区详情",
            session_id="summary-result-ref-detail-priority",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(detail["answer_kind"], "business")
        self.assertEqual(detail["capability"], "detail")
        self.assertEqual(detail["blocks"][0]["block_type"], "detail_card")

    async def test_legacy_context_is_upgraded_to_context_v3_and_supports_unique_place_alias_follow_up(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="legacy-upgrade-context-v3",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        legacy_context = {
            key: value
            for key, value in summary["turn_context"].items()
            if key
            not in {
                "context_version",
                "query_state",
                "follow_up_targets",
                "result_refs",
                "last_closed_turn_id",
                "action_targets",
            }
        }

        follow_up = await self.service.reply(
            message="这些地方呢",
            session_id="legacy-upgrade-context-v3",
            turn_id=2,
            current_context=legacy_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "group")
        self.assertEqual(follow_up["turn_context"]["context_version"], 3)
        self.assertEqual(follow_up["turn_context"]["action_targets"], [])

    async def test_legacy_summary_context_without_alert_snapshot_rebuilds_record_list(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="legacy-summary-record-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        record_count = summary["blocks"][0]["metrics"]["record_count"]
        legacy_context = {
            **summary["turn_context"],
            "derived_sets": {
                "device_snapshot_id": summary["turn_context"]["derived_sets"].get("device_snapshot_id"),
                "record_snapshot_id": None,
                "region_group_snapshot_id": None,
            },
        }

        listing = await self.service.reply(
            message=f"这{record_count}条记录详情",
            session_id="legacy-summary-record-list",
            turn_id=2,
            current_context=legacy_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertEqual(listing["blocks"][0]["pagination"]["total_count"], record_count)
        self.assertTrue(listing["turn_context"]["derived_sets"].get("record_snapshot_id"))

    async def test_capability_question_returns_guidance_instead_of_time_clarification(self) -> None:
        reply = await self.service.reply(
            message="你好，你可以为我做点什么",
            session_id="capability-question",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["capability"], "none")
        self.assertIn("支持", reply["final_text"])

    async def test_short_noisy_chinese_returns_safe_hint_instead_of_time_clarification(self) -> None:
        reply = await self.service.reply(
            message="比你好",
            session_id="short-noisy-input",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["capability"], "none")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "safe_hint")
        self.assertNotIn("你想查看的时间段是", reply["final_text"])

    async def test_llm_guard_intercepts_non_business_noun_phrase_before_time_clarification(self) -> None:
        reply = await self.service.reply(
            message="上岛咖啡京东卡",
            session_id="llm-guard-noise",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["capability"], "none")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "safe_hint")
        self.assertNotIn("你想查看的时间段是", reply["final_text"])
        self.assertIn("墒情", reply["final_text"])

    async def test_llm_guard_intercepts_non_business_question_before_time_clarification(self) -> None:
        for turn_id, message in enumerate(("京东卡可以提现吗", "今天午饭吃什么"), start=1):
            reply = await self.service.reply(
                message=message,
                session_id="llm-guard-noise-questions",
                turn_id=turn_id,
                current_context=None,
                timezone="Asia/Shanghai",
            )

            self.assertEqual(reply["answer_kind"], "guidance")
            self.assertEqual(reply["blocks"][0]["guidance_reason"], "safe_hint")
            self.assertNotIn("你想查看的时间段是", reply["final_text"])

    async def test_province_summary_keeps_jiangsu_scope_label(self) -> None:
        reply = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="jiangsu-summary",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "summary")
        self.assertIn("江苏省", reply["final_text"])

    async def test_summary_without_time_returns_guidance_with_inheritable_region_context(self) -> None:
        reply = await self.service.reply(
            message="江苏最新的墒情情况",
            session_id="jiangsu-missing-time",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["capability"], "none")
        self.assertIn("你想查看的时间段是", reply["final_text"])
        self.assertEqual(reply["turn_context"]["topic_family"], "data")
        self.assertEqual(
            reply["turn_context"]["resolved_entities"],
            [{"kind": "province", "canonical_name": "江苏省"}],
        )

    async def test_time_only_follow_up_reuses_region_from_clarification_context(self) -> None:
        clarification = await self.service.reply(
            message="江苏最新的墒情情况",
            session_id="jiangsu-clarification-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="7天",
            session_id="jiangsu-clarification-follow-up",
            turn_id=2,
            current_context=clarification["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertIn("江苏省", follow_up["final_text"])
        self.assertTrue(follow_up["query_ref"]["has_query"])
        self.assertFalse(self.guard.calls)

    async def test_time_only_follow_up_reuses_prior_city_scope(self) -> None:
        summary = await self.service.reply(
            message="最近南京市墒情情况",
            session_id="nanjing-time-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="最近一个月",
            session_id="nanjing-time-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertIn("南京市", follow_up["final_text"])
        self.assertFalse(self.guard.calls)

    async def test_time_only_follow_up_reuses_prior_global_warning_summary_scope(self) -> None:
        summary = await self.service.reply(
            message="2月6号 全省出现墒情预警信息的点位有多少个",
            session_id="global-warning-summary-time-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="2月1号呢",
            session_id="global-warning-summary-time-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertEqual(follow_up["turn_context"]["time_window"]["start_time"], "2026-02-01 00:00:00")
        self.assertEqual(follow_up["turn_context"]["time_window"]["end_time"], "2026-02-01 23:59:59")
        self.assertIn("2026-02-01至2026-02-01", follow_up["final_text"])
        self.assertTrue(follow_up["query_ref"]["has_query"])
        self.assertNotIn("对象还不够明确", follow_up["final_text"])

    async def test_city_follow_up_inherits_prior_time_window(self) -> None:
        summary = await self.service.reply(
            message="南通最近7天墒情怎么样",
            session_id="city-follow-up-inherits-time",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="那海安市呢",
            session_id="city-follow-up-inherits-time",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertIn("海安市", follow_up["final_text"])
        self.assertIn("2026-04-07", follow_up["final_text"])
        self.assertNotIn("南通市", follow_up["final_text"])

    async def test_third_turn_device_follow_up_inherits_latest_region_and_original_time_window(self) -> None:
        first = await self.service.reply(
            message="南通最近7天墒情怎么样",
            session_id="third-turn-device-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        second = await self.service.reply(
            message="那如东县呢",
            session_id="third-turn-device-follow-up",
            turn_id=2,
            current_context=first["turn_context"],
            timezone="Asia/Shanghai",
        )
        third = await self.service.reply(
            message="那其中 SNS00204333 呢",
            session_id="third-turn-device-follow-up",
            turn_id=3,
            current_context=second["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(third["answer_kind"], "business")
        self.assertEqual(third["capability"], "detail")
        self.assertIn("SNS00204333", third["final_text"])
        self.assertIn("南通市如东县", third["final_text"])
        self.assertIn("2026-04-07", third["final_text"])

    async def test_detail_time_only_follow_up_keeps_detail_capability(self) -> None:
        detail = await self.service.reply(
            message="SNS00204333 最近怎么样",
            session_id="detail-time-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="那最近30天呢",
            session_id="detail-time-follow-up",
            turn_id=2,
            current_context=detail["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertEqual(follow_up["blocks"][0]["block_type"], "summary_card")
        self.assertIn("SNS00204333", follow_up["final_text"])

    async def test_detail_explicit_new_region_follow_up_keeps_detail_capability(self) -> None:
        detail = await self.service.reply(
            message="如东县详情",
            session_id="detail-object-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="那海安市呢",
            session_id="detail-object-follow-up",
            turn_id=2,
            current_context=detail["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "detail")
        self.assertEqual(follow_up["blocks"][0]["block_type"], "detail_card")
        self.assertIn("海安市", follow_up["final_text"])

    async def test_summary_to_detail_then_time_only_follow_up_stays_detail(self) -> None:
        summary = await self.service.reply(
            message="南通最近7天墒情怎么样",
            session_id="summary-detail-time-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        detail = await self.service.reply(
            message="如东县详情",
            session_id="summary-detail-time-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="那最近30天呢",
            session_id="summary-detail-time-follow-up",
            turn_id=3,
            current_context=detail["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "detail")
        self.assertEqual(follow_up["blocks"][0]["block_type"], "detail_card")
        self.assertIn("如东县", follow_up["final_text"])

    async def test_detail_context_full_summary_question_resets_to_summary(self) -> None:
        detail = await self.service.reply(
            message="如东县详情",
            session_id="detail-to-summary-reset",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        fresh = await self.service.reply(
            message="海安市最近怎么样",
            session_id="detail-to-summary-reset",
            turn_id=2,
            current_context=detail["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(fresh["answer_kind"], "business")
        self.assertEqual(fresh["capability"], "summary")
        self.assertEqual(fresh["blocks"][0]["block_type"], "summary_card")
        self.assertIn("海安市", fresh["final_text"])

    async def test_detail_context_prefixed_full_summary_question_still_resets_to_summary(self) -> None:
        detail = await self.service.reply(
            message="如东县详情",
            session_id="detail-to-prefixed-summary-reset",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        fresh = await self.service.reply(
            message="那海安市最近怎么样",
            session_id="detail-to-prefixed-summary-reset",
            turn_id=2,
            current_context=detail["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(fresh["answer_kind"], "business")
        self.assertEqual(fresh["capability"], "summary")
        self.assertEqual(fresh["blocks"][0]["block_type"], "summary_card")
        self.assertIn("海安市", fresh["final_text"])

    async def test_correction_follow_up_replaces_previous_region_without_reasking_time(self) -> None:
        summary = await self.service.reply(
            message="如东县最近7天墒情怎么样",
            session_id="correction-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        corrected = await self.service.reply(
            message="不是如东县，是如皋市",
            session_id="correction-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(corrected["answer_kind"], "business")
        self.assertEqual(corrected["capability"], "summary")
        self.assertIn("如皋市", corrected["final_text"])
        self.assertNotIn("如东县", corrected["final_text"])
        self.assertNotIn("你想查看的时间段是", corrected["final_text"])

    async def test_closing_context_does_not_inherit_on_next_turn(self) -> None:
        summary = await self.service.reply(
            message="南通最近7天墒情怎么样",
            session_id="closing-reset",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        closing = await self.service.reply(
            message="谢谢",
            session_id="closing-reset",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )
        follow_up = await self.service.reply(
            message="如东县呢",
            session_id="closing-reset",
            turn_id=3,
            current_context=closing["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertTrue(closing["conversation_closed"])
        self.assertTrue(closing["turn_context"]["closed"])
        self.assertEqual(follow_up["answer_kind"], "guidance")
        self.assertEqual(follow_up["blocks"][0]["guidance_reason"], "clarification")
        self.assertIn("时间段", follow_up["final_text"])

    async def test_stale_context_follow_up_requires_clarification(self) -> None:
        summary = await self.service.reply(
            message="南通最近7天墒情怎么样",
            session_id="stale-context",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        stale_context = {
            **summary["turn_context"],
            "follow_up_targets": [
                {
                    **summary["turn_context"]["follow_up_targets"][0],
                    "last_active_turn_id": 1,
                }
            ],
            "query_state": {
                **summary["turn_context"]["query_state"],
                "last_active_turn_id": 1,
            },
        }

        reply = await self.service.reply(
            message="那个情况呢",
            session_id="stale-context",
            turn_id=8,
            current_context=stale_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "clarification")
        self.assertIn("重新", reply["final_text"])

    async def test_ambiguous_region_reference_requires_clarification(self) -> None:
        summary = await self.service.reply(
            message="最近7天整体墒情怎么样",
            session_id="ambiguous-ref",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        reply = await self.service.reply(
            message="上面那个地区呢",
            session_id="ambiguous-ref",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "clarification")
        self.assertIn("不够明确", reply["final_text"])

    async def test_low_confidence_inherited_scope_requires_clarification(self) -> None:
        summary = await self.service.reply(
            message="最近南京墒情情况",
            session_id="low-confidence-inherit",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        low_conf_context = {
            **summary["turn_context"],
            "query_state": {
                **summary["turn_context"]["query_state"],
                "slot_confidence": {
                    **summary["turn_context"]["query_state"]["slot_confidence"],
                    "city": "medium",
                },
            },
            "follow_up_targets": [
                {
                    **summary["turn_context"]["follow_up_targets"][0],
                    "slot_confidence": {
                        **summary["turn_context"]["follow_up_targets"][0]["slot_confidence"],
                        "city": "medium",
                    },
                }
            ],
        }

        reply = await self.service.reply(
            message="最近一个月",
            session_id="low-confidence-inherit",
            turn_id=2,
            current_context=low_conf_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "guidance")
        self.assertEqual(reply["blocks"][0]["guidance_reason"], "clarification")
        self.assertIn("明确", reply["final_text"])

    async def test_global_scope_group_query_does_not_inherit_prior_city_scope(self) -> None:
        summary = await self.service.reply(
            message="最近南京市墒情情况",
            session_id="nanjing-global-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="最近一个月按地区汇总墒情数据",
            session_id="nanjing-global-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "group")
        self.assertEqual(follow_up["blocks"][0]["group_by"], "region")
        self.assertGreater(len(follow_up["blocks"][0]["rows"]), 1)
        self.assertFalse(self.guard.calls)

    async def test_explicit_province_follow_up_overrides_prior_city_scope(self) -> None:
        summary = await self.service.reply(
            message="最近一个月南京市墒情情况",
            session_id="nanjing-province-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="整个江苏",
            session_id="nanjing-province-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertIn("江苏省", follow_up["final_text"])
        self.assertNotIn("南京市", follow_up["final_text"])
        self.assertFalse(self.guard.calls)

    async def test_later_explicit_city_in_same_message_overrides_earlier_city_reference(self) -> None:
        summary = await self.service.reply(
            message="最近一个月南京市墒情情况",
            session_id="city-override-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="我第一个问的是南京，后面都是问别的。我现在问南通，最近墒情怎么样",
            session_id="city-override-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertIn("南通市", follow_up["final_text"])
        self.assertNotIn("南京市", follow_up["final_text"])
        self.assertFalse(self.guard.calls)

    async def test_rule_topic_does_not_bleed_into_data_follow_up(self) -> None:
        rule = await self.service.reply(
            message="墒情预警规则是什么",
            session_id="rule-topic",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(rule["capability"], "rule")
        self.assertEqual(rule["turn_context"]["topic_family"], "rule")
        self.assertEqual(rule["blocks"][0]["block_type"], "rule_card")
        self.assertEqual(rule["blocks"][0]["display_mode"], "evidence_only")

        follow_up = await self.service.reply(
            message="这些点位呢",
            session_id="rule-topic",
            turn_id=2,
            current_context=rule["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "guidance")
        self.assertEqual(follow_up["capability"], "none")
        self.assertIn("数据查询上下文", follow_up["final_text"])

    async def test_summary_focus_devices_can_be_filtered_by_county_without_live_query(self) -> None:
        summary = await self.service.reply(
            message="最近三个月整体墒情怎么样",
            session_id="subset-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        filtered = await self.service.reply(
            message="这些点位里只看如皋市",
            session_id="subset-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(filtered["answer_kind"], "business")
        self.assertEqual(filtered["capability"], "list")
        self.assertEqual(filtered["blocks"][0]["block_type"], "list_table")
        self.assertTrue(filtered["blocks"][0]["rows"])
        self.assertTrue(all(row["county"] == "如皋市" for row in filtered["blocks"][0]["rows"]))

    async def test_rule_then_template_switches_topic_family(self) -> None:
        rule = await self.service.reply(
            message="墒情预警规则是什么",
            session_id="rule-template",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        template = await self.service.reply(
            message="那模板呢",
            session_id="rule-template",
            turn_id=2,
            current_context=rule["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(template["answer_kind"], "business")
        self.assertEqual(template["capability"], "template")
        self.assertEqual(template["turn_context"]["topic_family"], "template")
        self.assertEqual(template["blocks"][0]["block_type"], "template_card")
        self.assertEqual(template["blocks"][0]["display_mode"], "evidence_only")
        self.assertTrue(template["blocks"][0]["template_text"])

    async def test_typo_template_request_does_not_fall_back_to_time_clarification(self) -> None:
        reply = await self.service.reply(
            message="预警模版",
            session_id="template-typo",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "template")
        self.assertEqual(reply["turn_context"]["topic_family"], "template")
        self.assertEqual(reply["blocks"][0]["block_type"], "template_card")
        self.assertNotIn("你想查看的时间段是", reply["final_text"])

    async def test_rule_then_typo_template_follow_up_switches_topic_family(self) -> None:
        rule = await self.service.reply(
            message="墒情预警规则是什么",
            session_id="rule-typo-template",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        template = await self.service.reply(
            message="那模版呢",
            session_id="rule-typo-template",
            turn_id=2,
            current_context=rule["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(template["answer_kind"], "business")
        self.assertEqual(template["capability"], "template")
        self.assertEqual(template["turn_context"]["topic_family"], "template")
        self.assertEqual(template["blocks"][0]["block_type"], "template_card")
        self.assertNotIn("你想查看的时间段是", template["final_text"])

    async def test_template_output_for_triggered_device_warning_renders_real_notice(self) -> None:
        self.repository.records.append(
            {
                "id": 990001,
                "sn": "SNS00213807",
                "gatewayid": "GW-TEST-1",
                "sensorid": "S-TEST-1",
                "unitid": "U-TEST-1",
                "city": "南京市",
                "county": "江宁区",
                "time": "2026-04-13 23:59:58",
                "create_time": "2026-04-13 23:59:58",
                "water20cm": 30.0,
                "water40cm": 31.0,
                "water60cm": 32.0,
                "water80cm": 33.0,
                "t20cm": 18.0,
                "t40cm": 17.0,
                "t60cm": 16.0,
                "t80cm": 15.0,
                "water20cmfieldstate": 1,
                "water40cmfieldstate": 1,
                "water60cmfieldstate": 1,
                "water80cmfieldstate": 1,
                "t20cmfieldstate": 1,
                "t40cmfieldstate": 1,
                "t60cmfieldstate": 1,
                "t80cmfieldstate": 1,
                "lat": 32.0,
                "lon": 118.0,
            }
        )

        reply = await self.service.reply(
            message="按模板输出 SNS00213807 最新预警",
            session_id="template-render-warning",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "template")
        self.assertIn("SNS00213807", reply["final_text"])
        self.assertIn("30.0%", reply["final_text"])
        self.assertIn("heavy_drought", reply["final_text"])
        self.assertNotIn("mock", reply["final_text"].lower())
        self.assertEqual(reply["blocks"][0]["block_type"], "template_card")
        self.assertEqual(reply["blocks"][0]["display_mode"], "evidence_only")
        self.assertEqual(reply["blocks"][0]["warning_level"], "heavy_drought")
        self.assertEqual(reply["blocks"][0]["rendered_text"], reply["final_text"])
        self.assertEqual(reply["blocks"][0]["latest_record"]["sn"], "SNS00213807")

    async def test_template_output_prefers_latest_triggered_warning_record_over_latest_plain_record(self) -> None:
        self.repository.records.append(
            {
                "id": 990003,
                "sn": "SNS00213807",
                "gatewayid": "GW-TEST-3",
                "sensorid": "S-TEST-3",
                "unitid": "U-TEST-3",
                "city": "镇江市",
                "county": "镇江经开区",
                "time": "2026-04-12 23:59:58",
                "create_time": "2026-04-12 23:59:58",
                "water20cm": 30.0,
                "water40cm": 31.0,
                "water60cm": 32.0,
                "water80cm": 33.0,
                "t20cm": 18.0,
                "t40cm": 17.0,
                "t60cm": 16.0,
                "t80cm": 15.0,
                "water20cmfieldstate": 1,
                "water40cmfieldstate": 1,
                "water60cmfieldstate": 1,
                "water80cmfieldstate": 1,
                "t20cmfieldstate": 1,
                "t40cmfieldstate": 1,
                "t60cmfieldstate": 1,
                "t80cmfieldstate": 1,
                "lat": 32.0,
                "lon": 118.0,
            }
        )

        reply = await self.service.reply(
            message="按模板输出 SNS00213807 最新预警",
            session_id="template-render-latest-warning-record",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "template")
        self.assertIn("SNS00213807", reply["final_text"])
        self.assertIn("30.0%", reply["final_text"])
        self.assertIn("heavy_drought", reply["final_text"])
        self.assertEqual(reply["blocks"][0]["warning_level"], "heavy_drought")
        self.assertEqual(reply["blocks"][0]["latest_record"]["create_time"], "2026-04-12 23:59:58")
        self.assertEqual(reply["blocks"][0]["rendered_text"], reply["final_text"])

    async def test_repeated_template_latest_warning_query_does_not_fall_back_to_time_clarification(self) -> None:
        first = await self.service.reply(
            message="按模板输出 SNS00213807 最新预警",
            session_id="template-repeat-no-time-clarify",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        second = await self.service.reply(
            message="按模板输出 SNS00213807 最新预警",
            session_id="template-repeat-no-time-clarify",
            turn_id=2,
            current_context=first["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(second["answer_kind"], "business")
        self.assertEqual(second["capability"], "template")
        self.assertNotIn("缺少可继承的时间范围", second["final_text"])
        self.assertNotIn("请直接补充具体时间段", second["final_text"])

    async def test_global_template_latest_warning_query_ignores_previous_device_context(self) -> None:
        self.repository.records.append(
            {
                "id": 990004,
                "sn": "SNS00990001",
                "gatewayid": "GW-TEST-4",
                "sensorid": "S-TEST-4",
                "unitid": "U-TEST-4",
                "city": "扬州市",
                "county": "邗江区",
                "time": "2026-04-13 23:59:59",
                "create_time": "2026-04-13 23:59:59",
                "water20cm": 30.0,
                "water40cm": 31.0,
                "water60cm": 32.0,
                "water80cm": 33.0,
                "t20cm": 18.0,
                "t40cm": 17.0,
                "t60cm": 16.0,
                "t80cm": 15.0,
                "water20cmfieldstate": 1,
                "water40cmfieldstate": 1,
                "water60cmfieldstate": 1,
                "water80cmfieldstate": 1,
                "t20cmfieldstate": 1,
                "t40cmfieldstate": 1,
                "t60cmfieldstate": 1,
                "t80cmfieldstate": 1,
                "lat": 32.0,
                "lon": 119.0,
            }
        )

        first = await self.service.reply(
            message="按模板输出 SNS00213807 最新预警",
            session_id="template-global-warning",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        second = await self.service.reply(
            message="按模板输出任何一条最新预警",
            session_id="template-global-warning",
            turn_id=2,
            current_context=first["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(second["answer_kind"], "business")
        self.assertEqual(second["capability"], "template")
        self.assertIn("SNS00990001", second["final_text"])
        self.assertIn("30.0%", second["final_text"])
        self.assertIn("heavy_drought", second["final_text"])
        self.assertEqual(second["blocks"][0]["warning_level"], "heavy_drought")
        self.assertEqual(second["blocks"][0]["latest_record"]["sn"], "SNS00990001")
        self.assertEqual(second["turn_context"]["query_state"]["slots"]["sn"], "SNS00990001")
        self.assertNotIn("SNS00213807当前没有符合预警条件", second["final_text"])

    async def test_template_output_for_device_without_warning_history_returns_no_warning_history_notice(self) -> None:
        self.repository.records.append(
            {
                "id": 990002,
                "sn": "SNS00213808",
                "gatewayid": "GW-TEST-2",
                "sensorid": "S-TEST-2",
                "unitid": "U-TEST-2",
                "city": "南京市",
                "county": "江宁区",
                "time": "2026-04-13 23:59:57",
                "create_time": "2026-04-13 23:59:57",
                "water20cm": 90.0,
                "water40cm": 91.0,
                "water60cm": 92.0,
                "water80cm": 93.0,
                "t20cm": 18.0,
                "t40cm": 17.0,
                "t60cm": 16.0,
                "t80cm": 15.0,
                "water20cmfieldstate": 1,
                "water40cmfieldstate": 1,
                "water60cmfieldstate": 1,
                "water80cmfieldstate": 1,
                "t20cmfieldstate": 1,
                "t40cmfieldstate": 1,
                "t60cmfieldstate": 1,
                "t80cmfieldstate": 1,
                "lat": 32.0,
                "lon": 118.0,
            }
        )

        reply = await self.service.reply(
            message="按模板输出 SNS00213808 最新预警",
            session_id="template-render-no-warning",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "template")
        self.assertIn("SNS00213808", reply["final_text"])
        self.assertIn("符合预警条件", reply["final_text"])
        self.assertNotIn("heavy_drought", reply["final_text"])
        self.assertIsNone(reply["blocks"][0]["warning_level"])
        self.assertIsNone(reply["blocks"][0]["rendered_text"])
        self.assertEqual(reply["blocks"][0]["latest_record"]["sn"], "SNS00213808")

    async def test_legacy_context_is_upgraded_to_context_v3(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="legacy-upgrade-context-v2",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        record_count = summary["blocks"][0]["metrics"]["record_count"]
        legacy_context = {
            key: value
            for key, value in summary["turn_context"].items()
            if key
            not in {
                "context_version",
                "query_state",
                "follow_up_targets",
                "result_refs",
                "last_closed_turn_id",
            }
        }

        follow_up = await self.service.reply(
            message=f"这{record_count}条记录详情",
            session_id="legacy-upgrade-context-v2",
            turn_id=2,
            current_context=legacy_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["turn_context"]["context_version"], 3)
        self.assertTrue(follow_up["turn_context"]["follow_up_targets"])

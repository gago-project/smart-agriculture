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
        ]
        self.guard = FakeLlmInputGuard(
            intercepted_inputs={"上岛咖啡京东卡", "京东卡可以提现吗", "今天午饭吃什么"}
        )
        self.service = DataAnswerService(repository=repository, llm_input_guard=self.guard)

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
        self.assertEqual(summary["blocks"][0]["block_type"], "summary_card")
        self.assertEqual(summary["blocks"][0]["display_mode"], "evidence_only")
        self.assertTrue(summary["query_ref"]["has_query"])
        self.assertTrue(summary["turn_context"]["derived_sets"]["focus_devices_snapshot_id"])

        focus_snapshot_id = summary["turn_context"]["derived_sets"]["focus_devices_snapshot_id"]
        listing = await self.service.reply(
            message="列出需要重点关注的点位",
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
        self.assertGreaterEqual(listing["blocks"][0]["pagination"]["total_count"], 0)

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

    async def test_summary_then_alert_record_follow_up_returns_record_list(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="summary-record-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        listing = await self.service.reply(
            message="这44条预警记录详情",
            session_id="summary-record-list",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertIn("预警记录", listing["blocks"][0]["title"])
        self.assertEqual(
            listing["blocks"][0]["pagination"]["total_count"],
            summary["blocks"][0]["metrics"]["alert_record_count"],
        )
        self.assertGreater(len(listing["blocks"][0]["rows"]), 1)

    async def test_record_list_follow_up_can_group_covered_regions(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="summary-region-group",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        listing = await self.service.reply(
            message="列出44条预警记录详情",
            session_id="summary-region-group",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        grouped = await self.service.reply(
            message="覆盖哪13个地区",
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
        self.assertEqual(len(grouped["blocks"][0]["rows"]), summary["blocks"][0]["metrics"]["alert_region_count"])
        self.assertIn("地区", grouped["final_text"])
        self.assertNotIn("当前整体墒情", grouped["final_text"])

    async def test_legacy_summary_context_without_alert_snapshot_rebuilds_record_list(self) -> None:
        summary = await self.service.reply(
            message="江苏最近墒情情况如何",
            session_id="legacy-summary-record-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )
        legacy_context = {
            **summary["turn_context"],
            "derived_sets": {
                "focus_devices_snapshot_id": summary["turn_context"]["derived_sets"].get("focus_devices_snapshot_id"),
                "focus_regions_snapshot_id": None,
            },
        }

        listing = await self.service.reply(
            message="这44条预警记录详情",
            session_id="legacy-summary-record-list",
            turn_id=2,
            current_context=legacy_context,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(listing["answer_kind"], "business")
        self.assertEqual(listing["capability"], "list")
        self.assertEqual(listing["blocks"][0]["block_type"], "list_table")
        self.assertEqual(
            listing["blocks"][0]["pagination"]["total_count"],
            summary["blocks"][0]["metrics"]["alert_record_count"],
        )
        self.assertTrue(listing["turn_context"]["derived_sets"].get("alert_records_snapshot_id"))

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
            message="最近南京墒情情况",
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

    async def test_global_scope_question_does_not_inherit_prior_city_scope(self) -> None:
        summary = await self.service.reply(
            message="最近南京墒情情况",
            session_id="nanjing-global-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="最近一个月最严重的地方",
            session_id="nanjing-global-follow-up",
            turn_id=2,
            current_context=summary["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "summary")
        self.assertNotIn("南京市", follow_up["final_text"])
        self.assertFalse(self.guard.calls)

    async def test_explicit_province_follow_up_overrides_prior_city_scope(self) -> None:
        summary = await self.service.reply(
            message="最近一个月南京墒情情况",
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
            message="最近一个月南京墒情情况",
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

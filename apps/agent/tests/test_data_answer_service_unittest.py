"""Unit tests for the server-backed deterministic data answer service."""

from __future__ import annotations

import unittest

from tests.support_repositories import SeedSoilRepository


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
        self.service = DataAnswerService(repository=repository)

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
        self.assertEqual(listing["blocks"][0]["pagination"]["snapshot_id"], focus_snapshot_id)
        self.assertGreaterEqual(listing["blocks"][0]["pagination"]["total_count"], 0)

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

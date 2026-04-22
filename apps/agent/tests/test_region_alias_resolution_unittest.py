"""Unit tests for region alias resolution."""

from __future__ import annotations

import asyncio
import unittest

from app.services.agent_service import SoilAgentService
from app.services.intent_slot_service import IntentSlotService
from support_repositories import SeedSoilRepository


class RegionAliasResolutionTest(unittest.TestCase):
    """Test cases for region alias resolution."""
    def setUp(self) -> None:
        """Prepare the shared fixtures for each test case."""
        self.repository = SeedSoilRepository()

    def parse(self, text: str):
        """Handle parse on the region alias resolution test."""
        async def run_case():
            service = IntentSlotService(repository=self.repository, qwen_client=None)
            return await service.parse(text, "region-alias")

        return asyncio.run(run_case())

    def test_city_short_name_should_resolve_to_canonical_city(self) -> None:
        """Verify city short name should resolve to canonical city."""
        result = self.parse("南京最近一个月的数据")

        self.assertEqual(result.slots.get("city_name"), "南京市")
        self.assertEqual(result.slots.get("time_range"), "last_30_days")

    def test_county_short_name_should_resolve_to_canonical_county(self) -> None:
        """Verify county short name should resolve to canonical county."""
        result = self.parse("如东最近怎么样")

        self.assertEqual(result.slots.get("county_name"), "如东县")
        self.assertEqual(result.intent, "soil_region_query")

    def test_city_short_name_should_keep_existing_summary_routing(self) -> None:
        """Verify city short name should keep existing summary routing."""
        result = self.parse("南通最近7天墒情怎么样")

        self.assertEqual(result.slots.get("city_name"), "南通市")
        self.assertEqual(result.intent, "soil_recent_summary")

    def test_typo_should_resolve_when_candidate_is_unique(self) -> None:
        """Verify typo should resolve when candidate is unique."""
        result = self.parse("苏洲最近一个月的数据")

        self.assertEqual(result.slots.get("city_name"), "苏州市")

    def test_batch_phrase_without_explicit_time_should_clarify(self) -> None:
        """Verify batch-like filler words no longer imply latest-batch queries."""
        result = self.parse("这批数据整体情况如何")

        self.assertEqual(result.intent, "clarification_needed")
        self.assertEqual(result.answer_type, "clarification_answer")
        self.assertNotIn("batch_id", result.slots)
        self.assertNotIn("city_name", result.slots)

    def test_batch_phrase_with_explicit_time_should_ignore_filler(self) -> None:
        """Verify batch-like filler words are ignored when real time exists."""
        result = self.parse("这次南京最近7天墒情怎么样")

        self.assertEqual(result.intent, "soil_recent_summary")
        self.assertEqual(result.answer_type, "soil_summary_answer")
        self.assertEqual(result.slots.get("city_name"), "南京市")
        self.assertEqual(result.slots.get("time_range"), "last_7_days")
        self.assertNotIn("batch_id", result.slots)

    def test_ambiguous_alias_should_clarify_without_query(self) -> None:
        """Verify ambiguous alias should clarify without query."""
        self.repository.extra_region_aliases = [
            {
                "alias_name": "新区",
                "canonical_name": "甲新区",
                "region_level": "county",
                "parent_city_name": "甲市",
                "parent_county_name": None,
                "alias_source": "manual",
            },
            {
                "alias_name": "新区",
                "canonical_name": "乙新区",
                "region_level": "county",
                "parent_city_name": "乙市",
                "parent_county_name": None,
                "alias_source": "manual",
            },
        ]
        service = SoilAgentService(repository=self.repository)
        result = service.chat("新区最近怎么样", session_id="ambiguous-region", turn_id=1)

        self.assertEqual(result["intent"], "clarification_needed")
        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["query_plan"], {})


if __name__ == "__main__":
    unittest.main()

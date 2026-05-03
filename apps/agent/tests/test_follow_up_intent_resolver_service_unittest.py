from __future__ import annotations

import unittest


class FollowUpIntentResolverServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.follow_up_intent_resolver_service import FollowUpIntentResolverService

        self.service = FollowUpIntentResolverService()
        self.base_context = {
            "topic_family": "data",
            "closed": False,
            "query_state": {
                "capability": "summary",
                "grain": "aggregate",
                "slots": {"city": "南通市", "county": None, "province": None, "sn": None},
                "slot_confidence": {"city": "high", "time": "high"},
                "slot_source": {"city": "explicit", "time": "explicit"},
                "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"},
                "last_active_turn_id": 3,
            },
            "follow_up_targets": [
                {
                    "target_key": "target_3_summary",
                    "capability": "summary",
                    "grain": "aggregate",
                    "slots": {"city": "南通市", "county": None, "province": None, "sn": None},
                    "slot_confidence": {"city": "high", "time": "high"},
                    "slot_source": {"city": "explicit", "time": "explicit"},
                    "time_window": {"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"},
                    "source_turn_id": 3,
                    "last_active_turn_id": 3,
                    "parent_target_key": None,
                }
            ],
            "result_refs": [
                {
                    "ref_key": "ref_1",
                    "target_key": "target_3_summary",
                    "ref_type": "region",
                    "label": "如东县",
                    "ordinal": 1,
                    "entity_payload": {"county": "如东县"},
                    "source_turn_id": 3,
                },
                {
                    "ref_key": "ref_2",
                    "target_key": "target_3_summary",
                    "ref_type": "region",
                    "label": "海门区",
                    "ordinal": 2,
                    "entity_payload": {"county": "海门区"},
                    "source_turn_id": 3,
                },
            ],
        }

    def test_returns_inherit_for_time_only_follow_up(self) -> None:
        result = self.service.resolve(
            text="最近一个月",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=True,
            turn_id=4,
        )

        self.assertEqual(result.operation, "inherit")

    def test_returns_replace_slot_for_explicit_new_region(self) -> None:
        result = self.service.resolve(
            text="那海安市呢",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": ["海安市"], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "replace_slot")

    def test_returns_correct_slot_for_negative_correction(self) -> None:
        result = self.service.resolve(
            text="不是如东县，是如皋市",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": ["如东县", "如皋市"], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "correct_slot")

    def test_returns_switch_capability_for_detail_request(self) -> None:
        result = self.service.resolve(
            text="看详情",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "switch_capability")

    def test_returns_subset_for_subset_phrase(self) -> None:
        result = self.service.resolve(
            text="这些点位里只看如皋市",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": ["如皋市"], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "subset")

    def test_returns_drilldown_ref_for_ordinal_reference(self) -> None:
        result = self.service.resolve(
            text="第一个地区呢",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "drilldown_ref")
        self.assertEqual(result.selected_ref["label"], "如东县")

    def test_returns_clarify_for_ambiguous_pronoun_reference(self) -> None:
        result = self.service.resolve(
            text="上面那个地区呢",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "clarify")
        self.assertEqual(result.clarify_reason, "ambiguous_ref")

    def test_explicit_template_query_with_device_is_treated_as_standalone(self) -> None:
        result = self.service.resolve(
            text="按模板输出 SNS00213807 最新预警",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": ["SNS00213807"]},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "standalone")

    def test_global_template_warning_query_without_entity_is_treated_as_standalone(self) -> None:
        result = self.service.resolve(
            text="按模板输出任何一条最新预警",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=False,
            turn_id=4,
        )

        self.assertEqual(result.operation, "standalone")

    def test_self_contained_warning_summary_query_with_new_time_window_is_treated_as_standalone(self) -> None:
        result = self.service.resolve(
            text="最近30天有没有需要重点关注的地区",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=True,
            turn_id=4,
        )

        self.assertEqual(result.operation, "standalone")

    def test_self_contained_warning_list_query_with_new_time_window_is_treated_as_standalone(self) -> None:
        result = self.service.resolve(
            text="最近7天出现预警的点位详情",
            current_context=self.base_context,
            extracted_entities={"province": [], "city": [], "county": [], "sn": []},
            time_has_signal=True,
            turn_id=4,
        )

        self.assertEqual(result.operation, "standalone")


if __name__ == "__main__":
    unittest.main()

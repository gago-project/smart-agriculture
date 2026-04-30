from __future__ import annotations

import unittest


class FollowUpActionResolverServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.follow_up_action_resolver_service import FollowUpActionResolverService

        self.service = FollowUpActionResolverService()
        self.base_context = {
            "topic_family": "data",
            "closed": False,
            "active_topic_turn_id": 3,
            "action_targets": [
                {
                    "target_key": "target_alert_records",
                    "capability": "list",
                    "grain": "record_list",
                    "subject_kind": "record",
                    "source_snapshot_id": "snap_records",
                    "source_snapshot_kind": "alert_records",
                    "group_by": None,
                    "count": 44,
                    "label": "44条预警记录",
                    "source_turn_id": 3,
                    "last_active_turn_id": 3,
                },
                {
                    "target_key": "target_focus_devices",
                    "capability": "list",
                    "grain": "device_list",
                    "subject_kind": "device",
                    "source_snapshot_id": "snap_devices",
                    "source_snapshot_kind": "focus_devices",
                    "group_by": None,
                    "count": 16,
                    "label": "16个重点关注点位",
                    "source_turn_id": 3,
                    "last_active_turn_id": 3,
                },
                {
                    "target_key": "target_regions",
                    "capability": "group",
                    "grain": "region_group",
                    "subject_kind": "region",
                    "source_snapshot_id": "snap_devices",
                    "source_snapshot_kind": "focus_devices",
                    "group_by": "region",
                    "count": 13,
                    "label": "13个地区",
                    "source_turn_id": 3,
                    "last_active_turn_id": 3,
                },
            ],
        }

    def test_returns_expand_target_for_region_detail_follow_up(self) -> None:
        result = self.service.resolve(text="13个地区详情", current_context=self.base_context, turn_id=4)

        self.assertEqual(result.operation, "expand_target")
        self.assertEqual(result.selected_action_target["capability"], "group")
        self.assertEqual(result.selected_action_target["subject_kind"], "region")

    def test_returns_expand_target_for_short_region_follow_up(self) -> None:
        result = self.service.resolve(text="13个地区呢", current_context=self.base_context, turn_id=4)

        self.assertEqual(result.operation, "expand_target")
        self.assertEqual(result.selected_action_target["group_by"], "region")

    def test_returns_expand_target_for_focus_device_detail(self) -> None:
        result = self.service.resolve(text="16个重点关注点位详情", current_context=self.base_context, turn_id=4)

        self.assertEqual(result.operation, "expand_target")
        self.assertEqual(result.selected_action_target["capability"], "list")
        self.assertEqual(result.selected_action_target["subject_kind"], "device")

    def test_returns_expand_target_for_alert_record_alias(self) -> None:
        result = self.service.resolve(text="44条异常记录", current_context=self.base_context, turn_id=4)

        self.assertEqual(result.operation, "expand_target")
        self.assertEqual(result.selected_action_target["subject_kind"], "record")

    def test_returns_expand_target_for_place_alias_without_count_when_unique(self) -> None:
        context = {
            **self.base_context,
            "action_targets": [self.base_context["action_targets"][2]],
        }

        result = self.service.resolve(text="这些地方呢", current_context=context, turn_id=4)

        self.assertEqual(result.operation, "expand_target")
        self.assertEqual(result.selected_action_target["subject_kind"], "region")

    def test_returns_clarify_when_count_mismatches_target(self) -> None:
        result = self.service.resolve(text="12个地区详情", current_context=self.base_context, turn_id=4)

        self.assertEqual(result.operation, "clarify")
        self.assertEqual(result.clarify_reason, "count_mismatch")

    def test_returns_none_for_stale_action_target(self) -> None:
        context = {
            **self.base_context,
            "action_targets": [
                {
                    **target,
                    "last_active_turn_id": 1,
                }
                for target in self.base_context["action_targets"]
            ],
        }

        result = self.service.resolve(text="13个地区详情", current_context=context, turn_id=8)

        self.assertEqual(result.operation, "clarify")
        self.assertEqual(result.clarify_reason, "stale_target")


if __name__ == "__main__":
    unittest.main()

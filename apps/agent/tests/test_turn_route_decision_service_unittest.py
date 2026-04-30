from __future__ import annotations

import unittest

from app.services.follow_up_action_resolver_service import FollowUpActionResult


class TurnRouteDecisionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.turn_route_decision_service import TurnRouteDecisionService

        self.service = TurnRouteDecisionService()

    def test_standalone_list_beats_follow_up_action_expand_when_new_query_signals_exist(self) -> None:
        action = FollowUpActionResult(
            operation="expand_target",
            selected_action_target={"target_key": "target_focus_devices"},
            subject_kind="device",
        )

        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=False,
            is_group_request=False,
            should_group_standalone=False,
            list_target="devices",
            should_list_standalone=True,
            action_result=action,
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=False,
        )

        self.assertEqual(result.route, "standalone_list")
        self.assertEqual(result.list_target, "devices")
        self.assertIn("standalone_signals", result.reason_codes)

    def test_follow_up_action_expand_beats_contextual_list_route(self) -> None:
        action = FollowUpActionResult(
            operation="expand_target",
            selected_action_target={"target_key": "target_focus_devices"},
            subject_kind="device",
        )

        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=False,
            is_group_request=False,
            should_group_standalone=False,
            list_target="devices",
            should_list_standalone=False,
            action_result=action,
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=False,
        )

        self.assertEqual(result.route, "follow_up_action_expand")
        self.assertIn("action_target_expand", result.reason_codes)

    def test_contextual_list_route_is_used_when_no_action_target_matches(self) -> None:
        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=False,
            is_group_request=False,
            should_group_standalone=False,
            list_target="devices",
            should_list_standalone=False,
            action_result=FollowUpActionResult(),
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=False,
        )

        self.assertEqual(result.route, "follow_up_list")
        self.assertEqual(result.list_target, "devices")

    def test_group_standalone_route_beats_follow_up_paths(self) -> None:
        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=False,
            is_group_request=True,
            should_group_standalone=True,
            list_target=None,
            should_list_standalone=False,
            action_result=FollowUpActionResult(),
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=False,
        )

        self.assertEqual(result.route, "standalone_group")
        self.assertIn("group_request", result.reason_codes)

    def test_safe_hint_route_is_used_before_summary_when_signals_are_absent(self) -> None:
        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=False,
            is_group_request=False,
            should_group_standalone=False,
            list_target=None,
            should_list_standalone=False,
            action_result=FollowUpActionResult(),
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=True,
        )

        self.assertEqual(result.route, "safe_hint")

    def test_summary_route_is_default_fallback(self) -> None:
        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=False,
            is_group_request=False,
            should_group_standalone=False,
            list_target=None,
            should_list_standalone=False,
            action_result=FollowUpActionResult(),
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=False,
        )

        self.assertEqual(result.route, "summary")

    def test_follow_up_detail_route_is_used_for_short_contextual_detail_questions(self) -> None:
        result = self.service.decide(
            has_explicit_detail=False,
            should_follow_up_detail=True,
            is_group_request=False,
            should_group_standalone=False,
            list_target=None,
            should_list_standalone=False,
            action_result=FollowUpActionResult(),
            is_compare_request=False,
            is_detail_request=False,
            should_safe_hint_before_summary=False,
        )

        self.assertEqual(result.route, "follow_up_detail")
        self.assertIn("detail_context", result.reason_codes)


if __name__ == "__main__":
    unittest.main()

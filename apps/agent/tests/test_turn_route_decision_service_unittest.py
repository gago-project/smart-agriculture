from __future__ import annotations

import unittest

from app.services.follow_up_action_resolver_service import FollowUpActionResult
from app.services.time_window_service import TimeWindowResolution


def _time_window(*, matched: bool = False, has_signal: bool = False) -> TimeWindowResolution:
    if not has_signal and not matched:
        return TimeWindowResolution()
    return TimeWindowResolution(
        matched=matched,
        has_time_signal=has_signal or matched,
        time_source="rule_relative",
        start_time="2026-04-07 00:00:00",
        end_time="2026-04-13 23:59:59",
    )


def _entities(*, province: str | None = None, city: str | None = None, county: str | None = None, sn: str | None = None) -> dict:
    return {
        "province": [province] if province else [],
        "city": [city] if city else [],
        "county": [county] if county else [],
        "sn": [sn] if sn else [],
        "resolved": [],
    }


class TurnRouteDecisionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.turn_route_decision_service import TurnRouteDecisionService

        self.service = TurnRouteDecisionService()

    def test_standalone_group_query_returns_query_shape_and_group_by(self) -> None:
        result = self.service.decide(
            message="2026-04-13 有哪些地方有墒情数据",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "standalone_group")
        self.assertEqual(result.group_by, "region")
        self.assertEqual(result.route_source, "direct")
        self.assertEqual(result.normalized_text, "2026-04-13 有哪些地方有墒情数据")
        self.assertEqual(result.query_shape.subject, "soil")
        self.assertEqual(result.query_shape.action, "group")
        self.assertEqual(result.query_shape.grain, "region")
        self.assertEqual(result.query_shape.mode, "standalone")
        self.assertIn("group_request", result.reason_codes)

    def test_normalized_text_and_route_source_are_reported_for_typo_query(self) -> None:
        result = self.service.decide(
            message="2026-04-13 又哪些地方有墒情数据",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "standalone_group")
        self.assertEqual(result.route_source, "normalized")
        self.assertEqual(result.normalized_text, "2026-04-13 有哪些地方有墒情数据")
        self.assertEqual(result.query_shape.action, "group")

    def test_standalone_list_beats_action_target_expand_when_new_query_signals_exist(self) -> None:
        action = FollowUpActionResult(
            operation="expand_target",
            selected_action_target={"target_key": "target_focus_devices"},
            subject_kind="device",
        )

        result = self.service.decide(
            message="3月20号全省出现墒情预警信息的点位是哪些",
            current_context={"topic_family": "data"},
            entities=_entities(),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=action,
        )

        self.assertEqual(result.route, "standalone_list")
        self.assertEqual(result.list_target, "devices")
        self.assertEqual(result.query_shape.action, "list")
        self.assertEqual(result.query_shape.grain, "device")
        self.assertEqual(result.query_shape.mode, "standalone")
        self.assertIn("standalone_signals", result.reason_codes)

    def test_follow_up_action_expand_beats_contextual_list_route(self) -> None:
        action = FollowUpActionResult(
            operation="expand_target",
            selected_action_target={"target_key": "target_focus_devices"},
            subject_kind="device",
        )

        result = self.service.decide(
            message="涉及的点位数据呢",
            current_context={
                "topic_family": "data",
                "primary_query_spec": {"grain": "record_list"},
                "query_state": {"capability": "summary"},
            },
            entities=_entities(),
            time_evidence=_time_window(),
            action_result=action,
        )

        self.assertEqual(result.route, "follow_up_action_expand")
        self.assertEqual(result.route_source, "action_target")
        self.assertEqual(result.query_shape.action, "list")
        self.assertEqual(result.query_shape.grain, "device")
        self.assertEqual(result.query_shape.mode, "action_target")

    def test_detail_request_with_region_detail_phrase_is_not_summary(self) -> None:
        result = self.service.decide(
            message="如东县详情",
            current_context={},
            entities=_entities(county="如东县"),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "explicit_detail")
        self.assertEqual(result.query_shape.action, "detail")
        self.assertEqual(result.query_shape.grain, "entity")
        self.assertEqual(result.query_shape.mode, "explicit_detail")

    def test_device_with_time_and_zenmeyang_defaults_to_summary_instead_of_detail(self) -> None:
        result = self.service.decide(
            message="SNS00204333最近7天怎么样",
            current_context={},
            entities=_entities(sn="SNS00204333"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "summary")
        self.assertEqual(result.query_shape.action, "summary")
        self.assertEqual(result.query_shape.mode, "standalone")

    def test_latest_record_phrase_routes_to_latest_record(self) -> None:
        result = self.service.decide(
            message="SNS00204333最新一条记录是什么",
            current_context={},
            entities=_entities(sn="SNS00204333"),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "latest_record")
        self.assertEqual(result.query_shape.action, "detail")
        self.assertEqual(result.query_shape.mode, "standalone")

    def test_count_query_routes_to_count_shape(self) -> None:
        result = self.service.decide(
            message="最近7天南通市涉及多少个点位",
            current_context={},
            entities=_entities(city="南通市"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "count")
        self.assertEqual(result.query_shape.action, "count")
        self.assertEqual(result.query_shape.grain, "device")

    def test_field_query_routes_to_field_shape(self) -> None:
        result = self.service.decide(
            message="SNS00204333最近7天40厘米含水量平均是多少",
            current_context={},
            entities=_entities(sn="SNS00204333"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "field")
        self.assertEqual(result.query_shape.action, "field")
        self.assertEqual(result.query_shape.mode, "standalone")

    def test_device_compare_query_with_two_sn_routes_to_compare(self) -> None:
        result = self.service.decide(
            message="SNS00204333和SNS00213807最近7天对比一下",
            current_context={},
            entities=_entities(sn="SNS00204333"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "compare")
        self.assertEqual(result.query_shape.action, "compare")
        self.assertEqual(result.query_shape.mode, "standalone")

    def test_time_window_compare_query_routes_to_compare(self) -> None:
        result = self.service.decide(
            message="南通市最近7天和前7天对比一下",
            current_context={},
            entities=_entities(city="南通市"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "compare")
        self.assertEqual(result.query_shape.action, "compare")
        self.assertEqual(result.query_shape.mode, "standalone")

    def test_safe_hint_route_is_used_before_summary_when_signals_are_absent(self) -> None:
        result = self.service.decide(
            message="比你好",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "safe_hint")
        self.assertEqual(result.query_shape.action, "guidance")
        self.assertEqual(result.query_shape.mode, "safe_hint")

    def test_summary_route_is_default_fallback(self) -> None:
        result = self.service.decide(
            message="南京最近一个月的数据",
            current_context={},
            entities=_entities(city="南京"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "summary")
        self.assertEqual(result.query_shape.action, "summary")
        self.assertEqual(result.query_shape.grain, "none")
        self.assertEqual(result.query_shape.mode, "standalone")


if __name__ == "__main__":
    unittest.main()

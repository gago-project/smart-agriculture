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


def _context(*, capability: str | None = None, grain: str | None = None) -> dict:
    payload: dict = {"topic_family": "data"}
    if capability:
        payload["query_state"] = {"capability": capability}
    if grain:
        payload["primary_query_spec"] = {"grain": grain}
    return payload


class TurnRouteQueryShapeMatrixTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.turn_route_decision_service import TurnRouteDecisionService

        self.service = TurnRouteDecisionService()

    def test_query_shape_matrix(self) -> None:
        matrix = [
            {
                "label": "group-direct-place-query",
                "message": "2026-04-13 有哪些地方有墒情数据",
                "current_context": {},
                "entities": _entities(),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "standalone_group",
                "action": "group",
                "grain": "region",
            },
            {
                "label": "group-follow-up-place-reference",
                "message": "这些地方呢",
                "current_context": _context(capability="summary", grain="aggregate"),
                "entities": _entities(),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "follow_up_group",
                "action": "group",
                "grain": "region",
            },
            {
                "label": "list-device-standalone",
                "message": "3月20号全省出现墒情预警信息的点位是哪些",
                "current_context": {},
                "entities": _entities(),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "standalone_list",
                "action": "list",
                "grain": "device",
            },
            {
                "label": "list-device-warning-detail-standalone",
                "message": "最近7天出现预警的点位详情",
                "current_context": {},
                "entities": _entities(),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "standalone_list",
                "action": "list",
                "grain": "device",
            },
            {
                "label": "list-device-region-detail-standalone",
                "message": "南通市最近7天点位详情",
                "current_context": {},
                "entities": _entities(city="南通市"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "standalone_list",
                "action": "list",
                "grain": "device",
            },
            {
                "label": "list-device-follow-up-action-target",
                "message": "涉及的点位数据呢",
                "current_context": _context(capability="summary", grain="record_list"),
                "entities": _entities(),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(
                    operation="expand_target",
                    selected_action_target={"target_key": "target_focus_devices"},
                    subject_kind="device",
                ),
                "route": "follow_up_action_expand",
                "action": "list",
                "grain": "device",
            },
            {
                "label": "list-record-follow-up",
                "message": "这44条记录详情",
                "current_context": _context(capability="summary", grain="aggregate"),
                "entities": _entities(),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "follow_up_list",
                "action": "list",
                "grain": "record",
            },
            {
                "label": "list-record-contextual-verb",
                "message": "列出预警记录",
                "current_context": _context(capability="summary", grain="record_list"),
                "entities": _entities(),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "follow_up_list",
                "action": "list",
                "grain": "record",
            },
            {
                "label": "detail-device",
                "message": "SNS00204333 最近怎么样",
                "current_context": {},
                "entities": _entities(sn="SNS00204333"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "summary",
                "action": "summary",
                "grain": "none",
            },
            {
                "label": "detail-region",
                "message": "如东县详情",
                "current_context": {},
                "entities": _entities(county="如东县"),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "explicit_detail",
                "action": "detail",
                "grain": "entity",
            },
            {
                "label": "summary-city-window",
                "message": "南京最近一个月的数据",
                "current_context": {},
                "entities": _entities(city="南京"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "summary",
                "action": "summary",
                "grain": "none",
            },
            {
                "label": "summary-global-window",
                "message": "最近7天整体墒情怎么样",
                "current_context": {},
                "entities": _entities(),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "summary",
                "action": "summary",
                "grain": "none",
            },
            {
                "label": "count-device-query",
                "message": "最近7天南通市涉及多少个点位",
                "current_context": {},
                "entities": _entities(city="南通市"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "count",
                "action": "count",
                "grain": "device",
            },
            {
                "label": "latest-record-query",
                "message": "SNS00204333最新一条记录是什么",
                "current_context": {},
                "entities": _entities(sn="SNS00204333"),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "latest_record",
                "action": "detail",
                "grain": "entity",
            },
            {
                "label": "field-aggregate-query",
                "message": "SNS00204333最近7天40厘米含水量平均是多少",
                "current_context": {},
                "entities": _entities(sn="SNS00204333"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "field",
                "action": "field",
                "grain": "entity",
            },
            {
                "label": "field-latest-depth-projection-query",
                "message": "SNS00204333最新一条记录的20cm、40cm、60cm、80cm含水量分别是多少",
                "current_context": {},
                "entities": _entities(sn="SNS00204333"),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "field",
                "action": "field",
                "grain": "entity",
            },
            {
                "label": "field-latest-latlon-query",
                "message": "SNS00204333最新记录的经纬度是多少",
                "current_context": {},
                "entities": _entities(sn="SNS00204333"),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "field",
                "action": "field",
                "grain": "entity",
            },
            {
                "label": "compare-entity-query",
                "message": "徐州和南通最近30天20厘米平均含水量谁更高",
                "current_context": {},
                "entities": _entities(city="徐州市"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "compare",
                "action": "compare",
                "grain": "entity",
            },
            {
                "label": "compare-warning-metric-query",
                "message": "徐州和南通最近30天哪个预警点位更多",
                "current_context": {},
                "entities": _entities(city="徐州市"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "compare",
                "action": "compare",
                "grain": "entity",
            },
            {
                "label": "compare-dual-sn-query",
                "message": "SNS00204333和SNS00213807最近7天对比一下",
                "current_context": {},
                "entities": {
                    "province": [],
                    "city": [],
                    "county": [],
                    "sn": ["SNS00204333", "SNS00213807"],
                    "resolved": [],
                },
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "compare",
                "action": "compare",
                "grain": "entity",
            },
            {
                "label": "compare-time-query",
                "message": "南通市最近7天和前7天对比一下",
                "current_context": {},
                "entities": _entities(city="南通市"),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(),
                "route": "compare",
                "action": "compare",
                "grain": "entity",
            },
        ]

        for case in matrix:
            with self.subTest(case["label"]):
                result = self.service.decide(
                    message=case["message"],
                    current_context=case["current_context"],
                    entities=case["entities"],
                    time_evidence=case["time_evidence"],
                    action_result=case["action_result"],
                )
                self.assertEqual(result.route, case["route"])
                self.assertEqual(result.query_shape.action, case["action"])
                self.assertEqual(result.query_shape.grain, case["grain"])

    def test_conflict_priority_matrix(self) -> None:
        cases = [
            {
                "label": "place-query-must-not-fall-into-list",
                "message": "哪些地方有数据",
                "current_context": {},
                "entities": _entities(),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "standalone_group",
                "forbidden_routes": {"standalone_list", "follow_up_list"},
            },
            {
                "label": "device-enumeration-must-not-fall-into-group",
                "message": "点位是哪些",
                "current_context": _context(capability="summary", grain="aggregate"),
                "entities": _entities(),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "follow_up_list",
                "forbidden_routes": {"standalone_group", "follow_up_group"},
            },
            {
                "label": "region-detail-must-not-fall-into-summary",
                "message": "如东县详情",
                "current_context": {},
                "entities": _entities(county="如东县"),
                "time_evidence": _time_window(),
                "action_result": FollowUpActionResult(),
                "route": "explicit_detail",
                "forbidden_routes": {"summary"},
            },
            {
                "label": "fresh-standalone-group-beats-old-action-target-context",
                "message": "2026-04-13 有哪些地方有墒情数据",
                "current_context": _context(capability="summary", grain="record_list"),
                "entities": _entities(),
                "time_evidence": _time_window(matched=True, has_signal=True),
                "action_result": FollowUpActionResult(
                    operation="expand_target",
                    selected_action_target={"target_key": "target_focus_devices"},
                    subject_kind="device",
                ),
                "route": "standalone_group",
                "forbidden_routes": {"follow_up_action_expand", "follow_up_list"},
            },
        ]

        for case in cases:
            with self.subTest(case["label"]):
                result = self.service.decide(
                    message=case["message"],
                    current_context=case["current_context"],
                    entities=case["entities"],
                    time_evidence=case["time_evidence"],
                    action_result=case["action_result"],
                )
                self.assertEqual(result.route, case["route"])
                self.assertNotIn(result.route, case["forbidden_routes"])


if __name__ == "__main__":
    unittest.main()

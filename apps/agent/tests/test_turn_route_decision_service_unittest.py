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

    def test_device_registry_count_platform_query(self) -> None:
        result = self.service.decide(
            message="目前平台接入了多少台土壤墒情仪？",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "device_registry_count")
        self.assertEqual(result.query_shape.subject, "device_registry")
        self.assertEqual(result.query_shape.action, "count")
        self.assertEqual(result.query_shape.grain, "total")

    def test_device_registry_count_total_query(self) -> None:
        result = self.service.decide(
            message="苏农云接入的墒情仪总数是多少",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "device_registry_count")
        self.assertEqual(result.query_shape.subject, "device_registry")

    def test_device_registry_count_province_query(self) -> None:
        result = self.service.decide(
            message="全省有多少台土壤墒情仪",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "device_registry_count")
        self.assertEqual(result.query_shape.action, "count")

    def test_device_registry_count_access_variant(self) -> None:
        result = self.service.decide(
            message="平台一共接入了多少套土壤墒情监测设备",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )

        self.assertEqual(result.route, "device_registry_count")

    def test_is_device_registry_count_request_detection(self) -> None:
        from app.services.turn_route_decision_service import TurnRouteDecisionService as Svc
        self.assertTrue(Svc._is_device_registry_count_request("目前平台接入了多少台土壤墒情仪"))
        self.assertTrue(Svc._is_device_registry_count_request("苏农云接入的墒情仪总数是多少"))
        self.assertTrue(Svc._is_device_registry_count_request("全省有多少台土壤墒情仪"))
        self.assertTrue(Svc._is_device_registry_count_request("平台一共接入了多少套土壤墒情监测设备"))
        self.assertTrue(Svc._is_device_registry_count_request("设备台账总数"))
        # should NOT match regular count queries
        self.assertFalse(Svc._is_device_registry_count_request("最近7天南通市涉及多少个点位"))
        self.assertFalse(Svc._is_device_registry_count_request("南京最近一个月的数据"))

    def test_device_registry_count_ledger_keyword(self) -> None:
        """SM-DEV-005: 「设备台账总量」关键词路由到 device_registry_count"""
        result = self.service.decide(
            message="设备台账总量是多少",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "device_registry_count")
        self.assertEqual(result.query_shape.subject, "device_registry")

    def test_device_registry_count_non_soil_device_excluded(self) -> None:
        """SM-DEV-006: 非土壤设备类型（虫情）不路由到 device_registry_count"""
        from app.services.turn_route_decision_service import TurnRouteDecisionService as Svc
        self.assertFalse(Svc._is_device_registry_count_request("接入了多少台虫情监测设备"))
        self.assertFalse(Svc._is_device_registry_count_request("平台有多少台摄像头"))
        self.assertFalse(Svc._is_device_registry_count_request("监控摄像头总共多少个"))

    def test_device_registry_count_regional_query_routes_to_registry(self) -> None:
        """SM-DEV-007: 带城市名的设备数量查询仍路由到 device_registry_count，由执行层落到地区范围"""
        result = self.service.decide(
            message="南京接入了多少台土壤墒情仪",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "device_registry_count")
        self.assertEqual(result.query_shape.subject, "device_registry")

    def test_device_registry_distribution_province_query(self) -> None:
        result = self.service.decide(
            message="土壤墒情仪分布在哪里",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "device_registry_distribution")
        self.assertEqual(result.query_shape.subject, "device_registry")
        self.assertEqual(result.query_shape.action, "distribution")
        self.assertEqual(result.query_shape.grain, "city")

    def test_device_registry_distribution_city_variant(self) -> None:
        result = self.service.decide(
            message="江苏省各地市有多少台墒情仪",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "device_registry_distribution")
        self.assertEqual(result.query_shape.subject, "device_registry")
        self.assertEqual(result.query_shape.grain, "city")

    def test_device_registry_county_detail_routes_when_city_entity_present(self) -> None:
        result = self.service.decide(
            message="南通市土壤墒情仪分布情况",
            current_context={},
            entities=_entities(city="南通市"),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "device_registry_county_detail")
        self.assertEqual(result.query_shape.subject, "device_registry")
        self.assertEqual(result.query_shape.action, "distribution")
        self.assertEqual(result.query_shape.grain, "county")

    def test_device_registry_county_detail_not_triggered_without_city_entity(self) -> None:
        result = self.service.decide(
            message="土壤墒情仪各县区分布",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertNotEqual(result.route, "device_registry_county_detail")

    def test_warning_rule_query_routes_to_warning_rule_description(self) -> None:
        result = self.service.decide(
            message="土壤墒情的预警规则是什么",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_rule_description")
        self.assertEqual(result.query_shape.subject, "warning_rule")
        self.assertEqual(result.query_shape.action, "describe")

    def test_warning_rule_heavy_drought_variant(self) -> None:
        result = self.service.decide(
            message="什么情况下会触发重旱预警",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(matched=False, has_signal=False),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_rule_description")

    def test_is_warning_rule_query_detection(self) -> None:
        from app.services.turn_route_decision_service import TurnRouteDecisionService as Svc

        self.assertTrue(Svc._is_warning_rule_query("土壤墒情的预警规则是什么"))
        self.assertTrue(Svc._is_warning_rule_query("重旱标准是什么"))
        self.assertTrue(Svc._is_warning_rule_query("预警阈值"))
        self.assertFalse(Svc._is_warning_rule_query("南通市最近7天有多少预警记录"))
        self.assertFalse(Svc._is_warning_rule_query("最近7天有哪些预警"))

    def test_warning_list_route_with_time_signal(self) -> None:
        result = self.service.decide(
            message="最近7天南通市哪些点位出现了预警",
            current_context={},
            entities=_entities(city="南通市"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_list")
        self.assertEqual(result.query_shape.subject, "warning")
        self.assertEqual(result.query_shape.action, "list")

    def test_warning_count_route(self) -> None:
        result = self.service.decide(
            message="上周南通市有多少条预警记录",
            current_context={},
            entities=_entities(city="南通市"),
            time_evidence=_time_window(matched=True, has_signal=True),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_count")
        self.assertEqual(result.query_shape.subject, "warning")
        self.assertEqual(result.query_shape.action, "count")

    def test_warning_rule_query_not_matched_as_warning_record(self) -> None:
        result = self.service.decide(
            message="土壤墒情的预警规则是什么",
            current_context={},
            entities=_entities(),
            time_evidence=_time_window(),
            action_result=FollowUpActionResult(),
        )
        self.assertEqual(result.route, "warning_rule_description")

    def test_is_warning_record_query_detection(self) -> None:
        from app.services.turn_route_decision_service import TurnRouteDecisionService as Svc

        self.assertTrue(Svc._is_warning_record_query("最近7天南通市哪些点位出现了预警", has_time_signal=True))
        self.assertTrue(Svc._is_warning_record_query("上周有多少条预警", has_time_signal=True))
        self.assertTrue(Svc._is_warning_record_query("有哪些预警记录", has_time_signal=False))
        self.assertFalse(Svc._is_warning_record_query("预警规则是什么", has_time_signal=False))
        self.assertFalse(Svc._is_warning_record_query("预警阈值", has_time_signal=False))


if __name__ == "__main__":
    unittest.main()

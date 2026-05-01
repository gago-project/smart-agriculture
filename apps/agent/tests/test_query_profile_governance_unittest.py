"""Regression tests for deterministic query-profile governance behaviors."""

from __future__ import annotations

import unittest

from app.services.data_answer_service import DataAnswerService
from tests.support_repositories import SeedSoilRepository


def _alias(alias_name: str, canonical_name: str, region_level: str, parent_city_name: str | None = None) -> dict[str, str | None]:
    return {
        "alias_name": alias_name,
        "canonical_name": canonical_name,
        "region_level": region_level,
        "parent_city_name": parent_city_name,
        "alias_source": "test",
    }


def _field_record(
    *,
    record_id: int,
    sn: str,
    create_time: str,
    water20cm: float,
    water40cm: float,
    water60cm: float,
    water80cm: float,
    t20cm: float,
    t40cm: float,
    t60cm: float,
    t80cm: float,
    water20cmfieldstate: str | None,
) -> dict[str, object]:
    return {
        "id": record_id,
        "sn": sn,
        "gatewayid": "GW-TEST-1",
        "sensorid": "SENSOR-TEST-1",
        "unitid": "UNIT-TEST-1",
        "city": "南京市",
        "county": "江宁区",
        "time": create_time,
        "create_time": create_time,
        "water20cm": water20cm,
        "water40cm": water40cm,
        "water60cm": water60cm,
        "water80cm": water80cm,
        "t20cm": t20cm,
        "t40cm": t40cm,
        "t60cm": t60cm,
        "t80cm": t80cm,
        "water20cmfieldstate": water20cmfieldstate,
        "water40cmfieldstate": "1",
        "water60cmfieldstate": "1",
        "water80cmfieldstate": "1",
        "t20cmfieldstate": "1",
        "t40cmfieldstate": "1",
        "t60cmfieldstate": "1",
        "t80cmfieldstate": "1",
        "lat": 32.0617,
        "lon": 118.7969,
    }


class QueryProfileGovernanceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        repository = SeedSoilRepository()
        repository.extra_region_aliases = [
            _alias("江苏", "江苏省", "province"),
            _alias("南京", "南京市", "city"),
            _alias("南京市", "南京市", "city"),
            _alias("南通", "南通市", "city"),
            _alias("南通市", "南通市", "city"),
            _alias("徐州", "徐州市", "city"),
            _alias("徐州市", "徐州市", "city"),
            _alias("江宁", "江宁区", "county", "南京市"),
            _alias("江宁区", "江宁区", "county", "南京市"),
            _alias("如东", "如东县", "county", "南通市"),
            _alias("如东县", "如东县", "county", "南通市"),
            _alias("睢宁", "睢宁县", "county", "徐州市"),
            _alias("睢宁县", "睢宁县", "county", "徐州市"),
            _alias("沛县", "沛县", "county", "徐州市"),
            _alias("海安", "海安市", "county", "南通市"),
            _alias("海安市", "海安市", "county", "南通市"),
        ]
        repository.records.extend(
            [
                _field_record(
                    record_id=990001,
                    sn="SNS00990001",
                    create_time="2026-04-13 08:00:00",
                    water20cm=81.0,
                    water40cm=40.0,
                    water60cm=30.0,
                    water80cm=20.0,
                    t20cm=15.0,
                    t40cm=16.0,
                    t60cm=18.0,
                    t80cm=19.0,
                    water20cmfieldstate="2",
                ),
                _field_record(
                    record_id=990002,
                    sn="SNS00990001",
                    create_time="2026-04-12 08:00:00",
                    water20cm=82.0,
                    water40cm=50.0,
                    water60cm=35.0,
                    water80cm=25.0,
                    t20cm=15.5,
                    t40cm=16.5,
                    t60cm=20.0,
                    t80cm=20.0,
                    water20cmfieldstate="2",
                ),
                _field_record(
                    record_id=990003,
                    sn="SNS00990001",
                    create_time="2026-04-11 08:00:00",
                    water20cm=83.0,
                    water40cm=60.0,
                    water60cm=40.0,
                    water80cm=30.0,
                    t20cm=16.0,
                    t40cm=17.0,
                    t60cm=22.0,
                    t80cm=21.0,
                    water20cmfieldstate="2",
                ),
                _field_record(
                    record_id=990004,
                    sn="SNS00990002",
                    create_time="2026-04-13 09:00:00",
                    water20cm=78.0,
                    water40cm=45.0,
                    water60cm=32.0,
                    water80cm=21.0,
                    t20cm=14.5,
                    t40cm=15.5,
                    t60cm=17.5,
                    t80cm=18.5,
                    water20cmfieldstate="1",
                ),
                _field_record(
                    record_id=990005,
                    sn="SNS20406080",
                    create_time="2026-04-13 10:00:00",
                    water20cm=71.0,
                    water40cm=41.0,
                    water60cm=31.0,
                    water80cm=21.0,
                    t20cm=14.0,
                    t40cm=15.0,
                    t60cm=16.0,
                    t80cm=17.0,
                    water20cmfieldstate="1",
                ),
                _field_record(
                    record_id=990006,
                    sn="SNS20406080",
                    create_time="2026-04-12 10:00:00",
                    water20cm=72.0,
                    water40cm=42.0,
                    water60cm=32.0,
                    water80cm=22.0,
                    t20cm=14.5,
                    t40cm=15.5,
                    t60cm=17.0,
                    t80cm=18.0,
                    water20cmfieldstate="1",
                ),
                _field_record(
                    record_id=990007,
                    sn="SNS20406080",
                    create_time="2026-04-11 10:00:00",
                    water20cm=73.0,
                    water40cm=43.0,
                    water60cm=33.0,
                    water80cm=23.0,
                    t20cm=15.0,
                    t40cm=16.0,
                    t60cm=18.0,
                    t80cm=19.0,
                    water20cmfieldstate="1",
                ),
            ]
        )
        self.repository = repository
        self.service = DataAnswerService(repository=repository)

    async def test_device_time_how_question_defaults_to_summary_capability(self) -> None:
        reply = await self.service.reply(
            message="SNS00204333最近7天怎么样",
            session_id="qp-device-summary",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "summary")
        self.assertEqual(reply["blocks"][0]["block_type"], "summary_card")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["answer_mode"], "summary")
        self.assertIn("共有 7 条记录", reply["final_text"])

    async def test_latest_record_question_does_not_fall_back_to_recent_seven_day_window(self) -> None:
        reply = await self.service.reply(
            message="SNS00204333最新一条记录是什么",
            session_id="qp-latest-record",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "detail")
        self.assertEqual(reply["blocks"][0]["block_type"], "detail_card")
        self.assertTrue(reply["turn_context"]["query_state"]["query_profile"]["latest_only"])
        self.assertEqual(reply["blocks"][0]["latest_record"]["create_time"], "2026-04-13 23:59:17")
        self.assertNotIn("2026-04-07至2026-04-13", reply["final_text"])

    async def test_warning_device_count_question_returns_count_capability(self) -> None:
        reply = await self.service.reply(
            message="3月20号全省出现墒情预警信息的点位有多少个",
            session_id="qp-warning-device-count",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "count")
        self.assertEqual(reply["blocks"][0]["block_type"], "count_card")
        self.assertEqual(reply["blocks"][0]["count"], 12)
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["measure"], "alert_device_count")
        self.assertIn("12个点位", reply["final_text"])

    async def test_warning_record_count_zero_still_returns_zero_count_card(self) -> None:
        reply = await self.service.reply(
            message="最近30天如东县有多少条预警记录",
            session_id="qp-warning-record-count-zero",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "count")
        self.assertEqual(reply["blocks"][0]["block_type"], "count_card")
        self.assertEqual(reply["blocks"][0]["count"], 0)
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["measure"], "alert_record_count")
        self.assertIn("0条预警记录", reply["final_text"])

    async def test_warning_summary_query_uses_warning_focused_text(self) -> None:
        reply = await self.service.reply(
            message="最近30天全省有没有预警点位",
            session_id="qp-warning-summary",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "summary")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertIn("预警", reply["final_text"])
        self.assertNotIn("墒情概况", reply["final_text"])

    async def test_warning_top_counties_question_returns_ranked_group_rows(self) -> None:
        reply = await self.service.reply(
            message="最近30天预警最多的前5个县是哪些",
            session_id="qp-warning-top-counties",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "group")
        self.assertEqual(reply["blocks"][0]["block_type"], "group_table")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["measure"], "alert_device_count")
        self.assertEqual(reply["blocks"][0]["rows"][0]["county"], "睢宁县")
        self.assertEqual(reply["blocks"][0]["rows"][0]["alert_device_count"], 3)
        self.assertLessEqual(len(reply["blocks"][0]["rows"]), 5)

    async def test_warning_count_follow_up_device_details_inherits_warning_only_profile(self) -> None:
        counted = await self.service.reply(
            message="3月20号全省出现墒情预警信息的点位有多少个",
            session_id="qp-warning-count-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="点位详情呢",
            session_id="qp-warning-count-follow-up",
            turn_id=2,
            current_context=counted["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "list")
        self.assertEqual(follow_up["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertEqual(follow_up["turn_context"]["query_state"]["query_profile"]["answer_mode"], "list")

    async def test_warning_device_detail_query_returns_list_instead_of_detail(self) -> None:
        reply = await self.service.reply(
            message="最近7天出现预警的点位详情",
            session_id="qp-warning-device-detail-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "list")
        self.assertEqual(reply["blocks"][0]["block_type"], "list_table")
        self.assertIn("点位", reply["blocks"][0]["title"])

    async def test_compare_metric_question_returns_winner_and_metric_summary(self) -> None:
        reply = await self.service.reply(
            message="徐州和南通最近30天20厘米平均含水量谁更高",
            session_id="qp-compare-winner",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "compare")
        self.assertEqual(reply["blocks"][0]["block_type"], "compare_card")
        self.assertEqual(reply["blocks"][0]["metric"], "avg_water20cm")
        self.assertEqual(reply["blocks"][0]["winner"], "徐州市")
        self.assertIn("徐州市", reply["final_text"])
        self.assertIn("106.09%", reply["final_text"])

    async def test_warning_compare_metric_query_returns_winner_even_with_zero_side(self) -> None:
        reply = await self.service.reply(
            message="徐州和南通最近30天哪个预警点位更多",
            session_id="qp-warning-compare-winner",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "compare")
        self.assertEqual(reply["blocks"][0]["block_type"], "compare_card")
        self.assertEqual(reply["blocks"][0]["metric"], "alert_device_count")
        self.assertEqual(reply["blocks"][0]["winner"], "徐州市")
        self.assertEqual(reply["blocks"][0]["left_value"], 9)
        self.assertEqual(reply["blocks"][0]["right_value"], 0)
        self.assertIn("徐州市", reply["final_text"])

    async def test_dual_sn_compare_query_returns_compare_card(self) -> None:
        reply = await self.service.reply(
            message="SNS00204333和SNS00213807最近7天对比一下",
            session_id="qp-dual-sn-compare",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "compare")
        self.assertEqual(reply["blocks"][0]["block_type"], "compare_card")
        compared_entities = [row["entity"] for row in reply["blocks"][0]["rows"]]
        self.assertEqual(compared_entities, ["SNS00204333", "SNS00213807"])

    async def test_time_compare_question_returns_time_compare_mode(self) -> None:
        reply = await self.service.reply(
            message="南通市最近7天和前7天对比一下",
            session_id="qp-time-compare",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "compare")
        self.assertEqual(reply["blocks"][0]["compare_mode"], "time_compare")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["compare_mode"], "time_compare")

    async def test_field_aggregate_query_returns_numeric_aggregate_value(self) -> None:
        reply = await self.service.reply(
            message="SNS00990001最近7天40厘米含水量平均是多少",
            session_id="qp-field-aggregate",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["block_type"], "field_card")
        self.assertEqual(reply["blocks"][0]["field_mode"], "aggregate")
        self.assertEqual(reply["blocks"][0]["field"], "water40cm")
        self.assertEqual(reply["blocks"][0]["aggregation"], "avg")
        self.assertEqual(reply["blocks"][0]["value"], 50.0)
        self.assertIn("50.0", reply["final_text"])

    async def test_seed_field_aggregate_query_ignores_sn_digits_for_depth_matching(self) -> None:
        records = self.repository.filter_records(
            sn="SNS20406080",
            start_time="2026-04-07 00:00:00",
            end_time="2026-04-13 23:59:59",
        )
        valid_values = [float(record["water40cm"]) for record in records if record.get("water40cm") is not None]
        expected = round(sum(valid_values) / len(valid_values), 2)
        reply = await self.service.reply(
            message="SNS20406080最近7天40厘米含水量平均是多少",
            session_id="qp-seed-water40-aggregate",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["field"], "water40cm")
        self.assertEqual(reply["blocks"][0]["value"], expected)

    async def test_seed_temperature_aggregate_query_ignores_sn_digits_for_depth_matching(self) -> None:
        records = self.repository.filter_records(
            sn="SNS20406080",
            start_time="2026-04-07 00:00:00",
            end_time="2026-04-13 23:59:59",
        )
        valid_values = [float(record["t60cm"]) for record in records if record.get("t60cm") is not None]
        expected = round(sum(valid_values) / len(valid_values), 2)
        reply = await self.service.reply(
            message="SNS20406080最近7天60厘米温度平均是多少",
            session_id="qp-seed-t60-aggregate",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["field"], "t60cm")
        self.assertEqual(reply["blocks"][0]["value"], expected)

    async def test_field_projection_query_returns_requested_latest_raw_fields(self) -> None:
        reply = await self.service.reply(
            message="SNS00990001的gatewayid、sensorid、unitid是什么",
            session_id="qp-field-projection",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["block_type"], "field_card")
        self.assertEqual(reply["blocks"][0]["field_mode"], "latest_projection")
        self.assertEqual(reply["blocks"][0]["fields"], ["gatewayid", "sensorid", "unitid"])
        self.assertEqual(reply["blocks"][0]["values"]["gatewayid"], "GW-TEST-1")
        self.assertEqual(reply["blocks"][0]["values"]["sensorid"], "SENSOR-TEST-1")
        self.assertEqual(reply["blocks"][0]["values"]["unitid"], "UNIT-TEST-1")

    async def test_latest_projection_questions_with_duoshao_route_to_field(self) -> None:
        latest_record = self.repository.filter_records(sn="SNS00204333", limit=1)[0]
        reply = await self.service.reply(
            message="SNS00204333最新记录的经纬度是多少",
            session_id="qp-field-lat-lon",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["field_mode"], "latest_projection")
        self.assertEqual(reply["blocks"][0]["fields"], ["lat", "lon"])
        self.assertEqual(reply["blocks"][0]["values"]["lat"], latest_record["lat"])
        self.assertEqual(reply["blocks"][0]["values"]["lon"], latest_record["lon"])

    async def test_latest_multi_depth_projection_returns_requested_fields(self) -> None:
        latest_record = self.repository.filter_records(sn="SNS00204333", limit=1)[0]
        reply = await self.service.reply(
            message="SNS00204333最新一条记录的20cm、40cm、60cm、80cm含水量分别是多少",
            session_id="qp-field-depth-projection",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["field_mode"], "latest_projection")
        self.assertEqual(
            reply["blocks"][0]["fields"],
            ["water20cm", "water40cm", "water60cm", "water80cm"],
        )
        self.assertEqual(reply["blocks"][0]["values"]["water20cm"], latest_record["water20cm"])
        self.assertEqual(reply["blocks"][0]["values"]["water40cm"], latest_record["water40cm"])
        self.assertEqual(reply["blocks"][0]["values"]["water60cm"], latest_record["water60cm"])
        self.assertEqual(reply["blocks"][0]["values"]["water80cm"], latest_record["water80cm"])

    async def test_latest_record_query_returns_compact_fact_summary(self) -> None:
        reply = await self.service.reply(
            message="SNS00204333最新一条记录是什么",
            session_id="qp-latest-record-rich-text",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "detail")
        self.assertIn("20cm含水量", reply["final_text"])
        self.assertIn("位于", reply["final_text"])

    async def test_fieldstate_filtered_list_query_returns_only_abnormal_devices(self) -> None:
        reply = await self.service.reply(
            message="最近7天哪些点位的water20cmfieldstate不正常",
            session_id="qp-fieldstate-filtered-list",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        self.assertEqual(reply["answer_kind"], "business")
        self.assertEqual(reply["capability"], "field")
        self.assertEqual(reply["blocks"][0]["block_type"], "list_table")
        self.assertEqual(reply["turn_context"]["query_state"]["query_profile"]["answer_mode"], "field")
        self.assertTrue(all(row["sn"] == "SNS00990001" for row in reply["blocks"][0]["rows"]))
        self.assertIn("water20cmfieldstate", reply["blocks"][0]["columns"])

    async def test_group_follow_up_region_details_reuses_current_group_result_instead_of_clarifying(self) -> None:
        grouped = await self.service.reply(
            message="最近30天按地区汇总墒情数据",
            session_id="qp-group-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="地区详情呢",
            session_id="qp-group-follow-up",
            turn_id=2,
            current_context=grouped["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["answer_kind"], "business")
        self.assertEqual(follow_up["capability"], "group")
        self.assertEqual(follow_up["blocks"][0]["block_type"], "group_table")
        self.assertEqual(
            follow_up["blocks"][0]["pagination"]["total_count"],
            grouped["blocks"][0]["pagination"]["total_count"],
        )

    async def test_warning_group_follow_up_preserves_warning_profile_and_prior_grouping(self) -> None:
        grouped = await self.service.reply(
            message="最近30天预警最多的前5个县是哪些",
            session_id="qp-warning-group-follow-up",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        follow_up = await self.service.reply(
            message="地区详情呢",
            session_id="qp-warning-group-follow-up",
            turn_id=2,
            current_context=grouped["turn_context"],
            timezone="Asia/Shanghai",
        )

        self.assertEqual(follow_up["turn_context"]["query_state"]["query_profile"]["data_focus"], "warning_only")
        self.assertEqual(follow_up["turn_context"]["query_state"]["query_profile"]["group_by"], "county")
        self.assertEqual(follow_up["blocks"][0]["group_by"], "county")


if __name__ == "__main__":
    unittest.main()

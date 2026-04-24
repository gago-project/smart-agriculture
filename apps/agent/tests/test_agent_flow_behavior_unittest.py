"""Unit tests for agent flow behavior."""

import unittest

from app.llm.qwen_client import QwenClient
from app.services.agent_service import SoilAgentService
from support_repositories import SeedSoilRepository


EXPECTED_FILTER_KEYS = {"city", "county", "sn"}
SUPPORTED_SLOT_KEYS = {
    "aggregation",
    "audience",
    "batch_devices",
    "city",
    "county",
    "device_exists",
    "follow_up",
    "metric",
    "need_template",
    "raw_time_expr",
    "region_exists",
    "render_mode",
    "resolved_end_time",
    "resolved_start_time",
    "sn",
    "target_date",
    "time_explicit",
    "time_range",
    "top_n",
    "trend",
}


class AvailablePassthroughQwenClient(QwenClient):
    """Qwen test double that stays available without doing real network IO."""

    def __init__(self) -> None:
        """Initialize with a non-empty api key so the LLM path is exercised."""
        super().__init__(api_key="test-key")

    async def extract_intent_slots(self, *, user_input: str, session_id: str):
        """Force deterministic slot parsing in the surrounding service tests."""
        del user_input, session_id
        return None

    async def _request_json(self, *, messages: list[dict[str, str]]):
        """Return a stable answer after the payload is serialized successfully."""
        del messages
        return {"final_answer": "LLM polished answer"}


class AgentFlowBehaviorTest(unittest.TestCase):
    """Test cases for agent flow behavior."""
    def setUp(self):
        """Prepare the shared fixtures for each test case."""
        self.service = SoilAgentService(repository=SeedSoilRepository(), qwen_client=QwenClient(api_key=""))

    def assert_current_filters(self, result):
        """Verify current query-plan filters only use city/county/sn."""
        self.assertEqual(set(result["query_plan"].get("filters", {}).keys()), EXPECTED_FILTER_KEYS)

    def assert_current_slots(self, result):
        """Verify merged slots stay inside the current supported contract."""
        self.assertTrue(SUPPORTED_SLOT_KEYS.issuperset(result["merged_slots"].keys()))

    def test_recent_summary_should_use_last_7_days_window(self):
        """Verify recent summary should use last 7 days window."""
        result = self.service.chat("最近墒情怎么样", session_id="summary", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["merged_slots"].get("time_range"), "last_7_days")
        self.assertEqual(result["business_time"].get("resolution_mode"), "relative_window")
        self.assertEqual(result["query_plan"].get("sql_template"), "SQL-01")
        self.assert_current_filters(result)
        self.assert_current_slots(result)
        self.assertNotIn("当前样本", result["final_answer"])
        self.assertNotIn("数据来源", result["final_answer"])
        self.assertNotIn("最新业务时间", result["final_answer"])

    def test_batch_phrase_without_explicit_time_should_clarify(self):
        """Verify batch-like filler words without time should ask for time clarification."""
        result = self.service.chat("这批数据整体情况如何", session_id="batch", turn_id=1)

        self.assertEqual(result["intent"], "clarification_needed")
        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["query_plan"], {})
        self.assert_current_slots(result)
        self.assertIn("时间范围", result["final_answer"])

    def test_batch_phrase_with_explicit_time_should_ignore_filler(self):
        """Verify batch-like filler words are ignored when explicit time exists."""
        result = self.service.chat("这次南京最近7天墒情怎么样", session_id="batch-time", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["intent"], "soil_recent_summary")
        self.assertEqual(result["merged_slots"].get("city"), "南京市")
        self.assertEqual(result["merged_slots"].get("time_range"), "last_7_days")
        self.assert_current_slots(result)
        self.assert_current_filters(result)
        self.assertEqual(result["query_plan"].get("sql_template"), "SQL-01")

    def test_now_summary_should_resolve_from_latest_business_time(self):
        """Verify now summary should resolve from latest business time."""
        result = self.service.chat("现在的墒情", session_id="latest", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["merged_slots"].get("time_range"), "latest_business_time")
        self.assertEqual(result["business_time"].get("time_basis"), "latest_business_time")
        self.assertEqual(result["query_plan"].get("time_range", {}).get("mode"), "latest_business_time")

    def test_top_100_ranking_should_clarify_without_query(self):
        """Verify top 100 ranking should clarify without query."""
        result = self.service.chat("给我前100个最严重设备", session_id="rank", turn_id=1)

        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["execution_gate_result"].get("decision"), "clarify")
        self.assertEqual(result["query_plan"], {})
        self.assertIn("前 20", result["final_answer"])

    def test_unknown_device_should_return_fallback(self):
        """Verify unknown device should return fallback."""
        result = self.service.chat("SNS00299999 最近怎么样", session_id="fb", turn_id=1)

        self.assertEqual(result["answer_type"], "fallback_answer")
        self.assertIn("核对名称", result["final_answer"])
        self.assertEqual(result["intent"], "soil_device_query")
        self.assertEqual(result["query_plan"].get("query_type"), "fallback")
        self.assertEqual(result["query_plan"].get("sql_template"), "SQL-07")

    def test_context_should_inherit_recent_region(self):
        """Verify context should inherit recent region."""
        self.service.chat("如东县最近怎么样", session_id="ctx", turn_id=1)
        result = self.service.chat("那上周的呢", session_id="ctx", turn_id=2)

        self.assertEqual(result["answer_type"], "soil_detail_answer")
        self.assertEqual(result["context_used"].get("county"), "如东县")
        self.assertEqual(result["merged_slots"].get("county"), "如东县")
        self.assertEqual(result["merged_slots"].get("time_range"), "last_week")

    def test_available_qwen_path_should_still_persist_context_for_follow_up(self):
        """Verify available-Qwen generation does not break context persistence."""
        service = SoilAgentService(repository=SeedSoilRepository(), qwen_client=AvailablePassthroughQwenClient())

        first = service.chat("如东县最近怎么样", session_id="ctx-qwen", turn_id=1)
        follow = service.chat("那上周的呢", session_id="ctx-qwen", turn_id=2)

        self.assertEqual(first["final_status"], "verified_end")
        self.assertEqual(follow["answer_type"], "soil_detail_answer")
        self.assertEqual(follow["merged_slots"].get("county"), "如东县")
        self.assertEqual(follow["merged_slots"].get("time_range"), "last_week")

    def test_yesterday_region_query_should_resolve_to_full_day_window(self):
        """Verify yesterday questions resolve to one full natural-day window."""
        result = self.service.chat("如东县昨天怎么样", session_id="yesterday", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_detail_answer")
        self.assertEqual(result["intent"], "soil_region_query")
        self.assertEqual(result["merged_slots"].get("time_range"), "yesterday")
        self.assertEqual(result["business_time"].get("start_time"), "2026-04-12 00:00:00")
        self.assertEqual(result["business_time"].get("end_time"), "2026-04-12 23:59:59")
        self.assert_current_filters(result)

    def test_dynamic_last_n_days_should_resolve_and_query_without_batch_filters(self):
        """Verify dynamic last-N-day windows are supported end-to-end."""
        result = self.service.chat("南京近12天异常概况", session_id="dynamic-days", turn_id=1)

        self.assertEqual(result["intent"], "soil_anomaly_query")
        self.assertEqual(result["answer_type"], "soil_anomaly_answer")
        self.assertEqual(result["merged_slots"].get("time_range"), "last_12_days")
        self.assertEqual(result["business_time"].get("start_time"), "2026-04-02 00:00:00")
        self.assertEqual(result["business_time"].get("end_time"), "2026-04-13 23:59:59")
        self.assert_current_filters(result)

    def test_weather_question_should_be_boundary_answer(self):
        """Verify weather question should be boundary answer."""
        result = self.service.chat("查一下明天天气", session_id="bound", turn_id=1)

        self.assertEqual(result["answer_type"], "boundary_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["intent"], "out_of_scope")

    def test_all_devices_trend_should_block(self):
        """Verify all devices trend should block."""
        result = self.service.chat("查所有设备最近90天趋势", session_id="gate", turn_id=1)

        self.assertEqual(result["intent"], "soil_device_query")
        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["execution_gate_result"].get("decision"), "block")
        self.assertEqual(result["query_plan"], {})

    def test_warning_strict_mode_should_keep_template_body(self):
        """Verify warning strict mode should keep template body."""
        result = self.service.chat("按模板输出 SNS00204333 最新预警", session_id="warn", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_warning_answer")
        self.assertIn("SN 编号 SNS00204333", result["final_answer"])
        self.assertEqual(result["template_result"].get("render_mode"), "strict")

    def test_warning_strict_mode_should_support_seed_device_sns00213807(self):
        """Verify warning strict mode should support seed device sns00213807."""
        result = self.service.chat("按模板输出 SNS00213807 最新预警", session_id="warn-seed", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_warning_answer")
        self.assertIn("SNS00213807", result["final_answer"])
        self.assertNotEqual(result["final_status"], "fallback_end")

    def test_successful_query_should_write_query_log(self):
        """Verify successful query should write query log."""
        result = self.service.chat("最近墒情怎么样", session_id="log", turn_id=1)

        self.assertTrue(result["should_query"])
        self.assertGreaterEqual(len(self.service.query_log_repository.logs), 1)
        latest_log = self.service.query_log_repository.logs[-1]
        self.assertEqual(latest_log["query_type"], "recent_summary")
        self.assertEqual(latest_log["session_id"], "log")
        self.assertEqual(latest_log["turn_id"], 1)
        self.assertIn("SELECT", latest_log["executed_sql_text"])
        self.assertIn("FROM fact_soil_moisture", latest_log["executed_sql_text"])
        self.assertIn("records", latest_log["executed_result_json"])
        self.assertGreater(len(latest_log["executed_result_json"]["records"]), 0)

    def test_city_summary_should_hide_internal_source_and_latest_time(self):
        """Verify city summary should hide internal source and latest time."""
        result = self.service.chat("南通市最近7天墒情怎么样", session_id="summary-city", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertNotIn("当前样本", result["final_answer"])
        self.assertNotIn("数据来源", result["final_answer"])
        self.assertNotIn("最新业务时间", result["final_answer"])

    def test_ranking_answer_should_hide_internal_scoring_terms(self):
        """Verify ranking answer should hide internal scoring terms."""
        result = self.service.chat("过去一个月哪里最严重", session_id="ranking-copy", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_ranking_answer")
        self.assertNotIn("按综合风险排序", result["final_answer"])
        self.assertNotIn("risk_score", result["final_answer"])
        self.assertNotIn("异常分", result["final_answer"])
        self.assertNotIn("维度", result["final_answer"])

    def test_anomaly_answer_should_hide_rule_engine_name(self):
        """Verify anomaly answer should hide rule engine name."""
        result = self.service.chat("最近有没有异常", session_id="anomaly-copy", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_anomaly_answer")
        self.assertNotIn("SoilStatusRuleEngine", result["final_answer"])
        self.assertIn("异常点位", result["final_answer"])

    def test_large_device_ranking_should_block(self):
        """Verify large device ranking should block."""
        result = self.service.chat("全省近三年所有设备排名", session_id="rank-block", turn_id=1)

        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["execution_gate_result"].get("decision"), "block")
        self.assertEqual(result["query_plan"], {})

    def test_closing_turn_should_clear_context_and_not_query(self):
        """Verify closing utterance clears context inside same thread."""
        self.service.chat("如东县最近怎么样", session_id="closing", turn_id=1)
        closing = self.service.chat("谢谢", session_id="closing", turn_id=2)
        follow_up = self.service.chat("那上周的呢", session_id="closing", turn_id=3)

        self.assertEqual(closing["answer_type"], "closing_answer")
        self.assertTrue(closing["conversation_closed"])
        self.assertFalse(closing["should_query"])
        self.assertEqual(follow_up["answer_type"], "clarification_answer")
        self.assertFalse(follow_up["should_query"])

    def test_switch_region_follow_up_should_keep_anomaly_frame(self):
        """Verify explicit region switch inherits anomaly frame and time window."""
        self.service.chat("南京最近30天异常概况", session_id="switch-region", turn_id=1)
        result = self.service.chat("徐州呢？", session_id="switch-region", turn_id=2)

        self.assertEqual(result["answer_type"], "soil_anomaly_answer")
        self.assertEqual(result["intent"], "soil_anomaly_query")
        self.assertEqual(result["merged_slots"].get("city"), "徐州市")
        self.assertEqual(result["context_used"].get("inheritance_mode"), "carry_frame")
        self.assertEqual(result["business_time"].get("resolved_time_range"), "last_30_days")

    def test_ranking_follow_up_to_device_should_convert_to_detail(self):
        """Verify ranking follow up on device converts to detail query."""
        self.service.chat("哪个县最严重", session_id="rank-to-device", turn_id=1)
        result = self.service.chat("SNS00204333呢？", session_id="rank-to-device", turn_id=2)

        self.assertEqual(result["answer_type"], "soil_detail_answer")
        self.assertEqual(result["intent"], "soil_device_query")
        self.assertEqual(result["context_used"].get("inheritance_mode"), "convert_frame")

    def test_multi_slot_override_should_keep_anomaly_frame(self):
        """Verify region time and metric overrides keep compatible anomaly frame."""
        self.service.chat("南京最近30天异常概况", session_id="multi-override", turn_id=1)
        result = self.service.chat("盐城昨天20cm呢？", session_id="multi-override", turn_id=2)

        self.assertEqual(result["answer_type"], "soil_anomaly_answer")
        self.assertEqual(result["intent"], "soil_anomaly_query")
        self.assertEqual(result["merged_slots"].get("city"), "盐城市")
        self.assertEqual(result["merged_slots"].get("metric"), "water20cm")
        self.assertEqual(result["merged_slots"].get("time_range"), "yesterday")
        self.assertEqual(result["business_time"].get("resolved_time_range"), "yesterday")

    def test_advice_overlay_should_not_be_sticky_for_next_region_switch(self):
        """Verify advice turns do not become the next default query frame."""
        self.service.chat("最近有没有异常", session_id="advice-overlay", turn_id=1)
        self.service.chat("这种情况农户要注意什么", session_id="advice-overlay", turn_id=2)
        result = self.service.chat("徐州呢？", session_id="advice-overlay", turn_id=3)

        self.assertEqual(result["answer_type"], "soil_anomaly_answer")
        self.assertEqual(result["intent"], "soil_anomaly_query")
        self.assertEqual(result["merged_slots"].get("city"), "徐州市")
        self.assertNotEqual(result["query_plan"].get("query_type"), "latest_record")

    def test_context_dependent_short_follow_up_should_reach_boundary(self):
        """Verify context-dependent short follow-ups are not stopped by InputGuard."""
        self.service.chat("如东县最近怎么样", session_id="short-follow", turn_id=1)
        result = self.service.chat("那个情况呢", session_id="short-follow", turn_id=2)

        self.assertNotEqual(result["input_type"], "ambiguous_low_confidence")
        self.assertEqual(result["context_used"].get("inheritance_mode"), "carry_frame")
        self.assertEqual(result["merged_slots"].get("county"), "如东县")

    def test_complete_new_question_should_reset_frame(self):
        """Verify complete new question does not inherit old region."""
        self.service.chat("如东县最近怎么样", session_id="reset-frame", turn_id=1)
        result = self.service.chat("南京最近15天墒情怎么样", session_id="reset-frame", turn_id=2)

        self.assertEqual(result["intent"], "soil_recent_summary")
        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["merged_slots"].get("city"), "南京市")
        self.assertNotIn("county", result["merged_slots"])
        self.assertEqual(result["context_used"].get("inheritance_mode"), "reset_frame")

    def test_decayed_context_should_not_block_explicit_new_region(self):
        """Verify decay only blocks pure ellipsis, not explicit new entities."""
        session_id = "decay-new-region"
        for turn_id, message in enumerate(
            [
                "如东县最近怎么样",
                "最近墒情怎么样",
                "哪个市最严重",
                "最近有没有异常",
                "生成一条墒情预警",
            ],
            start=1,
        ):
            self.service.chat(message, session_id=session_id, turn_id=turn_id)
        result = self.service.chat("南京呢？", session_id=session_id, turn_id=6)

        self.assertNotEqual(result["answer_type"], "clarification_answer")
        self.assertEqual(result["merged_slots"].get("city"), "南京市")

    def test_five_year_anomaly_should_clarify_without_query(self):
        """Verify five year anomaly should clarify without query."""
        result = self.service.chat("查过去5年异常点位", session_id="anomaly-limit", turn_id=1)

        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["execution_gate_result"].get("decision"), "clarify")
        self.assertEqual(result["query_plan"], {})


if __name__ == "__main__":
    unittest.main()

import unittest

from app.services.agent_service import SoilAgentService
from support_repositories import SeedSoilRepository


class AgentFlowBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.service = SoilAgentService(repository=SeedSoilRepository())

    def test_recent_summary_should_use_last_7_days_window(self):
        result = self.service.chat("最近墒情怎么样", session_id="summary", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["merged_slots"].get("time_range"), "last_7_days")
        self.assertEqual(result["business_time"].get("resolution_mode"), "relative_window")
        self.assertEqual(result["query_plan"].get("sql_template"), "SQL-01")

    def test_latest_batch_summary_should_bind_latest_batch_id(self):
        result = self.service.chat("这批数据整体情况如何", session_id="batch", turn_id=1)
        expected_batch_id = self.service.repository.latest_batch_id()
        expected_count = len(
            [record for record in self.service.repository.records if record.get("batch_id") == expected_batch_id]
        )

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["merged_slots"].get("batch_id"), "latest_batch")
        self.assertEqual(result["business_time"].get("latest_batch_id"), expected_batch_id)
        self.assertEqual(result["query_plan"].get("filters", {}).get("batch_id"), expected_batch_id)
        self.assertEqual(len(result["query_result"].get("records", [])), expected_count)
        self.assertIn(f"{expected_count} 条", result["final_answer"])

    def test_now_summary_should_resolve_from_latest_business_time(self):
        result = self.service.chat("现在的墒情", session_id="latest", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["merged_slots"].get("time_range"), "latest_business_time")
        self.assertEqual(result["business_time"].get("time_basis"), "latest_business_time")
        self.assertEqual(result["query_plan"].get("time_range", {}).get("mode"), "latest_business_time")

    def test_top_100_ranking_should_clarify_before_query(self):
        result = self.service.chat("给我前100个最严重设备", session_id="rank", turn_id=1)

        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertIn("前 20", result["final_answer"])
        self.assertEqual(result["execution_gate_result"].get("decision"), "clarify")

    def test_unknown_region_should_return_fallback(self):
        result = self.service.chat("XX乡镇最近怎么样", session_id="fb", turn_id=1)

        self.assertEqual(result["answer_type"], "fallback_answer")
        self.assertIn("核对名称", result["final_answer"])
        self.assertEqual(result["intent"], "soil_region_query")
        self.assertEqual(result["query_plan"].get("query_type"), "fallback")
        self.assertEqual(result["query_plan"].get("sql_template"), "SQL-07")

    def test_context_should_inherit_recent_region(self):
        self.service.chat("如东县最近怎么样", session_id="ctx", turn_id=1)
        result = self.service.chat("那上周的呢", session_id="ctx", turn_id=2)

        self.assertEqual(result["answer_type"], "soil_detail_answer")
        self.assertEqual(result["context_used"].get("county_name"), "如东县")
        self.assertEqual(result["merged_slots"].get("county_name"), "如东县")
        self.assertEqual(result["merged_slots"].get("time_range"), "last_week")

    def test_weather_question_should_be_boundary_answer(self):
        result = self.service.chat("查一下明天天气", session_id="bound", turn_id=1)

        self.assertEqual(result["answer_type"], "boundary_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["intent"], "out_of_scope")

    def test_all_devices_trend_should_block_before_query(self):
        result = self.service.chat("查所有设备最近90天趋势", session_id="gate", turn_id=1)

        self.assertEqual(result["intent"], "soil_device_query")
        self.assertEqual(result["answer_type"], "clarification_answer")
        self.assertFalse(result["should_query"])
        self.assertEqual(result["execution_gate_result"].get("decision"), "block")
        self.assertEqual(result["query_plan"], {})

    def test_warning_strict_mode_should_keep_template_body(self):
        result = self.service.chat("按模板输出 SNS00204333 最新预警", session_id="warn", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_warning_answer")
        self.assertIn("SN 编号 SNS00204333", result["final_answer"])
        self.assertEqual(result["template_result"].get("render_mode"), "strict")

    def test_warning_strict_mode_should_support_seed_device_sns00213807(self):
        result = self.service.chat("按模板输出 SNS00213807 最新预警", session_id="warn-seed", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_warning_answer")
        self.assertIn("SNS00213807", result["final_answer"])
        self.assertNotEqual(result["final_status"], "fallback_end")

    def test_successful_query_should_write_query_log(self):
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


if __name__ == "__main__":
    unittest.main()

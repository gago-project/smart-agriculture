import unittest

from app.llm.qwen_client import QwenClient
from app.services.agent_service import SoilAgentService
from support_repositories import SeedSoilRepository


class Plan3MatrixContractTest(unittest.TestCase):
    def setUp(self):
        self.service = SoilAgentService(
            repository=SeedSoilRepository(),
            qwen_client=QwenClient(api_key=""),
        )

    def chat(self, message, *, session_id, turn_id=1):
        return self.service.chat(message, session_id=session_id, turn_id=turn_id)

    def assert_route(self, result, *, intent, answer_type, should_query, query_type=None, sql_template=None):
        self.assertEqual(result["intent"], intent)
        self.assertEqual(result["answer_type"], answer_type)
        self.assertEqual(result["should_query"], should_query)
        if query_type is None:
            self.assertEqual(result["query_plan"], {})
        else:
            self.assertEqual(result["query_plan"].get("query_type"), query_type)
        if sql_template is not None:
            self.assertEqual(result["query_plan"].get("sql_template"), sql_template)

    def test_cl_03_follow_up_without_context_should_clarify_without_query(self):
        result = self.chat("那个情况呢", session_id="plan3-cl-03")

        self.assertEqual(result["input_type"], "ambiguous_low_confidence")
        self.assert_route(
            result,
            intent="clarification_needed",
            answer_type="clarification_answer",
            should_query=False,
        )

    def test_su_03_city_recent_soil_question_should_use_summary_sql_01(self):
        result = self.chat("南通市最近7天墒情怎么样", session_id="plan3-su-03")

        self.assert_route(
            result,
            intent="soil_recent_summary",
            answer_type="soil_summary_answer",
            should_query=True,
            query_type="recent_summary",
            sql_template="SQL-01",
        )

    def test_rk_04_top_100_ranking_should_query_without_clarify(self):
        result = self.chat("给我前100个最严重设备", session_id="plan3-rk-04")

        self.assertEqual(result["execution_gate_result"].get("decision"), "pass")
        self.assert_route(
            result,
            intent="soil_severity_ranking",
            answer_type="soil_ranking_answer",
            should_query=True,
            query_type="severity_ranking",
            sql_template="SQL-02",
        )

    def test_rk_05_large_device_ranking_should_query_without_block(self):
        result = self.chat("全省近三年所有设备排名", session_id="plan3-rk-05")

        self.assertEqual(result["execution_gate_result"].get("decision"), "pass")
        self.assert_route(
            result,
            intent="soil_severity_ranking",
            answer_type="soil_ranking_answer",
            should_query=True,
            query_type="severity_ranking",
            sql_template="SQL-02",
        )

    def test_dt_02_device_anomaly_question_should_use_device_detail_sql_03(self):
        result = self.chat("SNS00204333 最近有没有异常", session_id="plan3-dt-02")

        self.assertEqual(result["input_type"], "business_direct")
        self.assert_route(
            result,
            intent="soil_device_query",
            answer_type="soil_detail_answer",
            should_query=True,
            query_type="device_detail",
            sql_template="SQL-03",
        )

    def test_dt_04_metric_follow_up_should_inherit_device_and_use_device_detail(self):
        session_id = "plan3-dt-04"
        self.chat("SNS00204333 最近怎么样", session_id=session_id, turn_id=1)
        result = self.chat("换成20cm看", session_id=session_id, turn_id=2)

        self.assertEqual(result["context_used"].get("device_sn"), "SNS00204333")
        self.assertEqual(result["merged_slots"].get("device_sn"), "SNS00204333")
        self.assert_route(
            result,
            intent="soil_device_query",
            answer_type="soil_detail_answer",
            should_query=True,
            query_type="device_detail",
            sql_template="SQL-03",
        )

    def test_dt_05_decayed_context_should_clarify_without_query(self):
        session_id = "plan3-dt-05"
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
            self.chat(message, session_id=session_id, turn_id=turn_id)
        result = self.chat("有没有问题", session_id=session_id, turn_id=6)

        self.assertEqual(result["input_type"], "business_colloquial")
        self.assert_route(
            result,
            intent="clarification_needed",
            answer_type="clarification_answer",
            should_query=False,
        )

    def test_an_04_anomaly_five_year_window_should_query_without_clarify(self):
        result = self.chat("查过去5年异常点位", session_id="plan3-an-04")

        self.assertEqual(result["execution_gate_result"].get("decision"), "pass")
        self.assert_route(
            result,
            intent="soil_anomaly_query",
            answer_type="soil_anomaly_answer",
            should_query=True,
            query_type="anomaly_list",
            sql_template="SQL-04",
        )

    def test_ad_02_farmer_advice_should_use_previous_anomaly_context(self):
        session_id = "plan3-ad-02"
        self.chat("最近有没有异常", session_id=session_id, turn_id=1)
        result = self.chat("这种情况农户要注意什么", session_id=session_id, turn_id=2)

        self.assert_route(
            result,
            intent="soil_management_advice",
            answer_type="soil_advice_answer",
            should_query=True,
            query_type="latest_record",
            sql_template="SQL-06",
        )

    def test_ad_03_greenhouse_advice_should_use_previous_anomaly_context(self):
        session_id = "plan3-ad-03"
        self.chat("最近有没有异常", session_id=session_id, turn_id=1)
        result = self.chat("这种情况大棚怎么处理", session_id=session_id, turn_id=2)

        self.assertEqual(result["merged_slots"].get("audience"), "greenhouse")
        self.assert_route(
            result,
            intent="soil_management_advice",
            answer_type="soil_advice_answer",
            should_query=True,
            query_type="latest_record",
            sql_template="SQL-06",
        )

    def test_pg_03_two_year_city_anomaly_should_query_without_shrink(self):
        result = self.chat("过去两年镇江市异常概况", session_id="plan3-pg-03")

        self.assertEqual(result["execution_gate_result"].get("decision"), "pass")
        self.assertEqual(result["answer_type"], "soil_anomaly_answer")
        self.assertTrue(result["should_query"])
        self.assertEqual(result["query_plan"].get("query_type"), "anomaly_list")


if __name__ == "__main__":
    unittest.main()

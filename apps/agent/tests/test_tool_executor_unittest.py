import asyncio
import unittest
from tests.support_repositories import SeedSoilRepository
from app.services.tool_executor_service import ToolExecutorService, ToolValidationError


class ToolExecutorServiceTest(unittest.TestCase):
    def setUp(self):
        self.repo = SeedSoilRepository()
        self.executor = ToolExecutorService(repository=self.repo)

    def test_rejects_top_n_above_20(self):
        with self.assertRaises(ToolValidationError) as ctx:
            asyncio.run(self.executor.execute(
                tool_name="query_soil_ranking",
                tool_args={
                    "start_time": "2025-04-14 00:00:00",
                    "end_time": "2025-04-20 23:59:59",
                    "aggregation": "county",
                    "top_n": 50,
                },
            ))
        self.assertIn("top_n", str(ctx.exception))

    def test_rejects_time_span_over_365_days_for_ranking(self):
        with self.assertRaises(ToolValidationError) as ctx:
            asyncio.run(self.executor.execute(
                tool_name="query_soil_ranking",
                tool_args={
                    "start_time": "2020-01-01 00:00:00",
                    "end_time": "2025-04-20 23:59:59",
                    "aggregation": "device",
                },
            ))
        self.assertIn("time_span", str(ctx.exception))

    def test_rejects_unknown_tool_name(self):
        with self.assertRaises(ToolValidationError):
            asyncio.run(self.executor.execute(
                tool_name="drop_all_tables",
                tool_args={"start_time": "2025-01-01 00:00:00", "end_time": "2025-01-07 23:59:59"},
            ))

    def test_rejects_missing_required_time_params(self):
        with self.assertRaises(ToolValidationError):
            asyncio.run(self.executor.execute(
                tool_name="query_soil_summary",
                tool_args={"city": "延安市"},
            ))

    def test_query_soil_summary_returns_aggregated_stats(self):
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_summary",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
            },
        ))
        # Returns aggregated overview, NOT raw records list
        self.assertIn("total_records", result)
        self.assertIn("avg_water20cm", result)
        self.assertIn("status_counts", result)
        self.assertIn("alert_count", result)
        self.assertIn("top_alert_regions", result)
        self.assertNotIn("records", result)  # raw records must NOT be present

    def test_query_soil_ranking_returns_sorted_top_n_items(self):
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_ranking",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "aggregation": "county",
                "top_n": 5,
            },
        ))
        # Returns sorted TopN items, NOT raw records
        self.assertIn("items", result)
        self.assertIn("top_n", result)
        self.assertEqual(result["top_n"], 5)
        self.assertNotIn("records", result)  # raw records must NOT be present
        # Items have rank field
        if result["items"]:
            self.assertIn("rank", result["items"][0])
            self.assertEqual(result["items"][0]["rank"], 1)

    def test_query_soil_ranking_items_are_truly_sorted(self):
        """Items must be sorted by severity: more alerts first."""
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_ranking",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "aggregation": "county",
                "top_n": 10,
            },
        ))
        items = result["items"]
        for i in range(len(items) - 1):
            self.assertGreaterEqual(items[i]["alert_count"], items[i + 1]["alert_count"],
                                    "Items must be sorted by alert_count descending")

    def test_query_soil_detail_returns_entity_evidence(self):
        result = asyncio.run(self.executor.execute(
            tool_name="query_soil_detail",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
            },
        ))
        self.assertIn("entity_type", result)
        self.assertIn("entity_name", result)
        self.assertIn("record_count", result)
        self.assertIn("latest_record", result)
        self.assertIn("alert_records", result)
        self.assertIn("status_summary", result)

    def test_diagnose_empty_result_returns_diagnosis(self):
        result = asyncio.run(self.executor.execute(
            tool_name="diagnose_empty_result",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "scenario": "region_exists",
                "city": "延安市",
            },
        ))
        # Returns structured diagnosis, NOT region_record_count
        self.assertIn("entity_exists", result)
        self.assertIn("diagnosis", result)
        self.assertIn("message", result)
        self.assertIn(result["diagnosis"], ("data_exists", "entity_not_found", "no_data_in_window"))

    def test_diagnose_empty_result_distinguishes_entity_not_found(self):
        """Diagnose returns entity_not_found for unknown regions."""
        result = asyncio.run(self.executor.execute(
            tool_name="diagnose_empty_result",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "scenario": "region_exists",
                "city": "不存在的城市XYZABC",
            },
        ))
        self.assertFalse(result["entity_exists"])
        self.assertEqual(result["diagnosis"], "entity_not_found")

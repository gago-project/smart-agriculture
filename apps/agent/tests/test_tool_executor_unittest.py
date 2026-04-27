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
                tool_name="get_soil_ranking",
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
                tool_name="get_soil_ranking",
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
                tool_name="get_soil_overview",
                tool_args={"city": "延安市"},
            ))

    def test_get_soil_overview_returns_records(self):
        result = asyncio.run(self.executor.execute(
            tool_name="get_soil_overview",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
            },
        ))
        self.assertIn("records", result)
        self.assertIsInstance(result["records"], list)

    def test_get_soil_ranking_returns_records_with_top_n(self):
        result = asyncio.run(self.executor.execute(
            tool_name="get_soil_ranking",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "aggregation": "county",
                "top_n": 5,
            },
        ))
        self.assertIn("records", result)
        self.assertEqual(result.get("top_n"), 5)

    def test_diagnose_empty_result_returns_region_count(self):
        result = asyncio.run(self.executor.execute(
            tool_name="diagnose_empty_result",
            tool_args={
                "start_time": "2025-01-01 00:00:00",
                "end_time": "2025-12-31 23:59:59",
                "scenario": "region_exists",
                "city": "延安市",
            },
        ))
        self.assertIn("region_record_count", result)

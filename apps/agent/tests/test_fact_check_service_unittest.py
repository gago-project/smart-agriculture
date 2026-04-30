from __future__ import annotations

import unittest

from app.schemas.state import QueryResultBundle
from app.services.fact_check_service import FactCheckService


class FactCheckServiceBundleRegressionTest(unittest.TestCase):
    def test_query_result_bundle_does_not_treat_items_method_as_ranking_data(self) -> None:
        service = FactCheckService()
        query_result = QueryResultBundle(
            entries=[
                {
                    "tool_name": "query_soil_summary",
                    "result": {
                        "total_records": 259,
                        "avg_water20cm": 95.39,
                        "device_count": 12,
                        "region_count": 4,
                    },
                }
            ]
        )

        result = service.verify(
            answer_type="soil_summary_answer",
            answer_bundle={"final_answer": "南通市近7天整体平稳，平均20厘米含水量约95.39%。"},
            query_result=query_result,
            tool_trace=[],
            answer_facts={"entity_name": "南通市", "total_records": 259, "avg_water20cm": 95.39},
            resolved_args={"start_time": "2026-04-07 00:00:00", "end_time": "2026-04-13 23:59:59"},
        )

        self.assertFalse(result["failed"])


if __name__ == "__main__":
    unittest.main()

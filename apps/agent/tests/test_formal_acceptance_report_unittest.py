"""Unit tests for the formal acceptance report helpers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HELPER_PATH = ROOT / "testdata/agent/soil-moisture/scripts/generate_formal_acceptance_report.py"


def load_helper():
    """Load the formal acceptance helper script as a Python module."""
    spec = importlib.util.spec_from_file_location("formal_acceptance_helper_tests", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FormalAcceptanceReportTest(unittest.TestCase):
    """Regression tests for live response parsing in the formal report."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.helper = load_helper()

    def build_business_response(self) -> dict[str, Any]:
        """Return a current live response shape for a business ranking answer."""
        return {
            "answer": "最近30天县区里最严重的是清江浦区。",
            "mode": "normal",
            "data": {
                "answer_type": "soil_ranking_answer",
                "output_mode": "normal",
                "fallback_reason": None,
                "guidance_reason": None,
                "input_type": "business_direct",
            },
            "evidence": {
                "tool_trace": [
                    {
                        "tool_name": "query_soil_ranking",
                    }
                ],
                "query_result": {
                    "entries": [
                        {
                            "tool_name": "query_soil_ranking",
                            "records": [{"sn": "SNS-001"}],
                        }
                    ]
                },
            },
        }

    def test_infer_actual_tool_reads_nested_tool_trace(self) -> None:
        """Tool inference should use the nested evidence.tool_trace payload."""
        response = self.build_business_response()

        actual_tool, _ = self.helper.infer_actual_tool(
            [],
            response,
            {"预期 answer_type": "soil_ranking_answer"},
        )

        self.assertEqual(actual_tool, "query_soil_ranking")

    def test_analyze_case_reads_nested_live_response_fields(self) -> None:
        """Case analysis should read answer/meta fields from the current response shape."""
        response = self.build_business_response()
        case = {
            "预期 Tool": "query_soil_ranking",
            "预期 answer_type": "soil_ranking_answer",
            "预期 output_mode": "normal",
            "预期 guidance_reason": "无",
            "预期 fallback_reason": "无",
            "是否域内业务问题": "是",
            "是否必须命中 Tool": "是",
            "当前回答": "最近30天县区里最严重的是清江浦区。",
        }

        analysis = self.helper.analyze_case(
            case,
            {"response": response, "logs": []},
            {"applicable": False},
        )

        self.assertEqual(analysis["actual_input_type"], "business_direct")
        self.assertEqual(analysis["actual_tool"], "query_soil_ranking")
        self.assertEqual(analysis["actual_answer_type"], "soil_ranking_answer")
        self.assertEqual(analysis["actual_output_mode"], "normal")
        self.assertEqual(analysis["consistency"], "结论一致")
        self.assertTrue(analysis["pass"])

    def test_infer_actual_fallback_reason_reads_nested_data(self) -> None:
        """Fallback reason should come from the nested data payload."""
        response = {
            "answer": "最近400天没有可用数据，建议缩小时间范围。",
            "mode": "fallback",
            "data": {
                "answer_type": "fallback_answer",
                "output_mode": None,
                "fallback_reason": "no_data",
                "guidance_reason": None,
                "input_type": "business_direct",
            },
            "evidence": {},
        }

        actual_reason = self.helper.infer_actual_fallback_reason(response, {})

        self.assertEqual(actual_reason, "no_data")

    def test_infer_actual_fallback_reason_does_not_mistake_no_anomaly_for_no_data(self) -> None:
        response = {
            "answer": "在该时间段内南通市没有出现需要关注的异常情况。",
            "mode": "data_query",
            "data": {
                "answer_type": "soil_detail_answer",
                "output_mode": "normal",
                "fallback_reason": None,
                "guidance_reason": None,
                "input_type": "business_direct",
            },
            "evidence": {},
        }

        actual_reason = self.helper.infer_actual_fallback_reason(response, {})

        self.assertIsNone(actual_reason)

    def test_build_db_truth_allows_non_query_assertions(self) -> None:
        """Assertions that explicitly say 'do not query' should not be treated as blockers."""
        result = self.helper.build_db_truth(
            {
                "数据库校验断言": "不查库；验证 ParameterResolver 的 should_clarify=true 拦截逻辑",
            }
        )

        self.assertEqual(result["applicable"], False)
        self.assertIsNone(result["blocker"])

    def test_analyze_case_does_not_fail_only_because_sample_answer_differs(self) -> None:
        """Different sample wording should not fail when the actual response matches the contract."""
        response = {
            "answer": "您的问题中有些信息需要确认：时间表达不够明确。你想查看的时间段是？例如 最近 7 天、上周、2026 年 4 月。",
            "mode": "analysis",
            "data": {
                "answer_type": "guidance_answer",
                "output_mode": None,
                "fallback_reason": None,
                "guidance_reason": "clarification",
                "input_type": "business_direct",
            },
            "evidence": {},
        }
        case = {
            "预期 Tool": "无",
            "预期 answer_type": "guidance_answer",
            "预期 output_mode": "无",
            "预期 guidance_reason": "clarification",
            "预期 fallback_reason": "无",
            "是否域内业务问题": "是",
            "是否必须命中 Tool": "否",
            "当前回答": "请补充明确的时间范围后重试。",
        }

        analysis = self.helper.analyze_case(
            case,
            {"response": response, "logs": []},
            {"applicable": False, "blocker": None},
        )

        self.assertEqual(analysis["actual_answer_type"], "guidance_answer")
        self.assertEqual(analysis["actual_guidance_reason"], "clarification")
        self.assertEqual(analysis["fact_status"], "是")
        self.assertTrue(analysis["pass"])

    def test_summarize_results_does_not_flag_expected_non_query_guidance_as_missing_tool(self) -> None:
        """Only cases that must hit a tool should contribute to the missing-tool blocker."""
        summary = self.helper.summarize_results(
            [
                {
                    "case": {
                        "CaseID": "SM-CONV-003",
                        "是否域内业务问题": "是",
                        "是否必须命中 Tool": "否",
                        "预期 answer_type": "guidance_answer",
                        "预期 output_mode": "无",
                        "预期 fallback_reason": "无",
                    },
                    "analysis": {
                        "pass": True,
                        "actual_tool": None,
                        "fact_status": "是",
                    },
                }
            ]
        )

        self.assertEqual(summary["business_without_tool"], [])

    def test_analyze_case_uses_actual_answer_for_fact_status(self) -> None:
        """An outdated sample answer should not make a factual actual answer fail the case."""
        response = {
            "answer": "最近7天南通市共有 259 条记录，整体平稳。",
            "mode": "data_query",
            "data": {
                "answer_type": "soil_summary_answer",
                "output_mode": "normal",
                "fallback_reason": None,
                "guidance_reason": None,
                "input_type": "business_direct",
            },
            "evidence": {
                "tool_trace": [{"tool_name": "query_soil_summary"}],
                "query_result": {"entries": [{"tool_name": "query_soil_summary", "records": [{"sn": "SNS-001"}]}]},
            },
        }
        case = {
            "预期 Tool": "query_soil_summary",
            "预期 answer_type": "soil_summary_answer",
            "预期 output_mode": "normal",
            "预期 guidance_reason": "无",
            "预期 fallback_reason": "无",
            "是否域内业务问题": "是",
            "是否必须命中 Tool": "是",
            "当前回答": "最近7天南通市没有数据。",
        }
        db_truth = {
            "applicable": True,
            "blocker": None,
            "truth": {"total_records": 259},
            "sql_blocks": [{"sql_type": "等效 SQL", "tool": "query_soil_summary", "sql": "SELECT 1"}],
        }

        analysis = self.helper.analyze_case(case, {"response": response, "logs": []}, db_truth)

        self.assertEqual(analysis["actual_answer_check"]["fact_status"], "是")
        self.assertEqual(analysis["fact_status"], "是")
        self.assertTrue(analysis["pass"])

    def test_analyze_case_uses_execution_logs_as_sql_evidence(self) -> None:
        response = {
            "answer": "最近30天横向对比，徐州市更需要优先关注。",
            "mode": "data_query",
            "data": {
                "answer_type": "soil_ranking_answer",
                "output_mode": "normal",
                "fallback_reason": None,
                "guidance_reason": None,
                "input_type": "business_direct",
            },
            "evidence": {
                "tool_trace": [{"tool_name": "query_soil_comparison"}],
                "query_result": {"entries": [{"tool_name": "query_soil_comparison"}]},
            },
        }
        case = {
            "预期 Tool": "query_soil_comparison",
            "预期 answer_type": "soil_ranking_answer",
            "预期 output_mode": "normal",
            "预期 guidance_reason": "无",
            "预期 fallback_reason": "无",
            "是否域内业务问题": "是",
            "是否必须命中 Tool": "是",
            "当前回答": "最近30天横向对比，徐州市更需要优先关注。",
        }
        db_truth = {
            "applicable": True,
            "blocker": None,
            "truth": {},
            "sql_blocks": [],
        }
        execution = {
            "response": response,
            "logs": [{"executed_sql_text": "SELECT 1", "query_type": "comparison"}],
        }

        analysis = self.helper.analyze_case(case, execution, db_truth)

        self.assertNotIn("业务 case 缺少 SQL / 等效 SQL。", analysis["failure_reasons"])


if __name__ == "__main__":
    unittest.main()

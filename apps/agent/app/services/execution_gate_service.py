"""Execution policy gate for expensive or unsafe data requests.

The gate runs after time/region resolution and before SQL execution.  Its job
is to either pass, ask for clarification, or block a request.  This is where
we keep hard product limits so downstream query code can stay simple and does
not need to second-guess user scope.
"""

from __future__ import annotations


from datetime import datetime
from typing import Any


class ExecutionGateService:
    """Evaluate query scope against fixed safety limits."""

    MAX_TOP_N = 20
    MAX_RANKING_DAYS = 365
    MAX_ANOMALY_DAYS = 180

    def evaluate(self, *, intent: str, slots: dict[str, Any], business_time: dict[str, Any]) -> dict[str, Any]:
        """Return pass/clarify/block/shrink decision for one query."""
        resolved_day_span = self._resolved_day_span(business_time)
        result = {
            "tool_name": "ExecutionGate",
            "decision": "pass",
            "allow_execute": True,
            "reason": "",
            "policy_decision": "pass",
            "violations": [],
            "message": "",
            "must_clarify": False,
            "blocked": False,
            "clarify_message": None,
            "block_message": None,
        }

        if intent == "clarification_needed":
            # If intent extraction already determined the request is too vague,
            # do not let any data query run.
            return {
                **result,
                "decision": "clarify",
                "allow_execute": False,
                "policy_decision": "clarify",
                "reason": "clarification_intent",
                "violations": [{"field": "intent", "reason": "clarification_needed"}],
                "message": "请补充地区、设备或时间范围后再查询。",
                "must_clarify": True,
                "clarify_message": "请补充地区、设备或时间范围后再查询。例如：如东县最近怎么样，或 SNS00204333 最近有没有异常。",
            }

        top_n = int(slots.get("top_n") or 0)
        aggregation = slots.get("aggregation")
        batch_devices = slots.get("batch_devices")

        if intent == "soil_severity_ranking" and top_n > self.MAX_TOP_N:
            return {
                **result,
                "decision": "clarify",
                "allow_execute": False,
                "policy_decision": "clarify",
                "reason": "top_n_exceeded",
                "violations": [{"field": "top_n", "reason": f"exceeds_{self.MAX_TOP_N}"}],
                "message": f"当前最多支持前 {self.MAX_TOP_N} 个结果，请缩小范围后再查。",
                "must_clarify": True,
                "clarify_message": f"当前最多支持查看前 {self.MAX_TOP_N} 个结果，你可以改问“前 {self.MAX_TOP_N} 个最严重设备”。",
            }

        if intent == "soil_severity_ranking" and aggregation == "device" and resolved_day_span > self.MAX_RANKING_DAYS:
            return {
                **result,
                "decision": "block",
                "allow_execute": False,
                "policy_decision": "block",
                "reason": "ranking_window_too_wide",
                "violations": [{"field": "time_range", "reason": f"exceeds_{self.MAX_RANKING_DAYS}_days"}],
                "message": "当前设备排名时间范围过大，已阻断查询。",
                "blocked": True,
                "block_message": "当前设备排名时间范围过大，请缩小到近一年内，或改查地区级排名。",
            }

        if intent == "soil_anomaly_query" and resolved_day_span > self.MAX_ANOMALY_DAYS:
            return {
                **result,
                "decision": "clarify",
                "allow_execute": False,
                "policy_decision": "clarify",
                "reason": "anomaly_window_too_wide",
                "violations": [{"field": "time_range", "reason": f"exceeds_{self.MAX_ANOMALY_DAYS}_days"}],
                "message": "异常查询时间范围过大，请缩小后重试。",
                "must_clarify": True,
                "clarify_message": "异常查询时间范围过大，请缩小到近 180 天内后再查。",
            }

        if intent == "soil_device_query" and batch_devices == "all":
            return {
                **result,
                "decision": "block",
                "allow_execute": False,
                "policy_decision": "block",
                "reason": "batch_device_query_blocked",
                "violations": [{"field": "batch_devices", "reason": "all_devices_query_not_allowed"}],
                "message": "暂不支持批量设备查询。",
                "blocked": True,
                "block_message": "暂不支持批量设备查询，请指定单个设备后再试。",
            }
        return result

    def _resolved_day_span(self, business_time: dict[str, Any]) -> int:
        """Return inclusive natural-day span from resolved start/end times."""
        start_dt = self._parse_datetime(business_time.get("start_time"))
        end_dt = self._parse_datetime(business_time.get("end_time"))
        if not start_dt or not end_dt or end_dt < start_dt:
            return 1
        return (end_dt.date() - start_dt.date()).days + 1

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse SQL timestamp text, returning `None` for unknown values."""
        if not value or value == "暂无":
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


__all__ = ["ExecutionGateService"]

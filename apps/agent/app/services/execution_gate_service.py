from __future__ import annotations

"""Execution policy gate for expensive or unsafe data requests.

The gate runs after time/region resolution and before SQL execution.  Its job
is to either pass, ask for clarification, block, or shrink a request.  This is
where we keep hard product limits so downstream query code can stay simple and
does not need to second-guess user scope.
"""

from datetime import datetime, timedelta
from typing import Any


class ExecutionGateService:
    """Evaluate query scope against fixed safety limits."""

    # Time ranges are normalized into approximate day counts for policy checks.
    # The exact SQL window is still carried in `business_time`.
    TIME_DAYS_MAP = {
        "latest": 1,
        "latest_business_time": 1,
        "exact_date": 1,
        "latest_batch": 1,
        "last_week": 7,
        "last_7_days": 7,
        "last_30_days": 30,
        "year_to_date": 365,
        "last_2_years": 730,
        "last_3_years": 1095,
        "last_5_years": 1825,
    }

    def evaluate(self, *, intent: str, slots: dict[str, Any], business_time: dict[str, Any]) -> dict[str, Any]:
        """Return pass/clarify/block/shrink decision for one query."""
        time_range = slots.get("time_range") or business_time.get("resolved_time_range") or "last_7_days"
        requested_days = self.TIME_DAYS_MAP.get(time_range, 1)
        result = {
            "tool_name": "ExecutionGate",
            "decision": "pass",
            "allow_execute": True,
            "requested_days": requested_days,
            "resolved_days": requested_days,
            "reason": "",
            "policy_decision": "pass",
            "violations": [],
            "message": "",
            "must_clarify": False,
            "blocked": False,
            "shrink_applied": False,
            "effective_business_time": None,
            "effective_slots": None,
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
        return result

    def _shrink_business_time(
        self,
        *,
        business_time: dict[str, Any],
        fallback_time_range: str,
        max_days: int,
    ) -> dict[str, Any]:
        """Create an effective time window capped to `max_days`."""
        effective_business_time = dict(business_time)
        latest_time = business_time.get("end_time") or business_time.get("latest_business_time")
        latest_dt = self._parse_datetime(latest_time)
        effective_business_time["resolved_time_range"] = fallback_time_range
        effective_business_time["resolution_mode"] = "relative_window"
        effective_business_time["time_basis"] = business_time.get("time_basis") or "latest_business_time"
        if latest_dt:
            effective_business_time["start_time"] = (latest_dt - timedelta(days=max_days - 1)).strftime("%Y-%m-%d %H:%M:%S")
            effective_business_time["end_time"] = latest_dt.strftime("%Y-%m-%d %H:%M:%S")
        return effective_business_time

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

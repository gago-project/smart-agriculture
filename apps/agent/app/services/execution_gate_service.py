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
        top_n = int(slots.get("top_n") or 5)
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
        if slots.get("trend") and slots.get("batch_devices") == "all":
            # All-device time series can explode in payload size and is not a
            # useful default UX, so we force the user to narrow scope.
            return {
                **result,
                "decision": "block",
                "allow_execute": False,
                "policy_decision": "block",
                "reason": "batch_device_trend_not_allowed",
                "violations": [{"field": "batch_devices", "reason": "batch_device_trend_not_allowed", "requested_value": "all"}],
                "message": "当前不支持一次性返回所有设备趋势。你可以指定一个设备 SN，或改查某个地区的概览趋势。",
                "blocked": True,
                "block_message": "当前不支持一次性返回所有设备趋势。你可以指定一个设备 SN，或改查某个地区的概览趋势。",
            }
        if slots.get("trend") and not any(slots.get(key) for key in ["device_sn", "city_name", "county_name", "town_name"]):
            return {
                **result,
                "decision": "clarify",
                "allow_execute": False,
                "policy_decision": "clarify",
                "reason": "trend_requires_filter",
                "violations": [{"field": "trend", "reason": "require_region_or_device_for_timeseries"}],
                "message": "趋势查询需要指定地区或设备。你可以问“南通市近一年墒情趋势”或“SNS00204333 近 90 天趋势”。",
                "must_clarify": True,
                "clarify_message": "趋势查询需要指定地区或设备。你可以问“南通市近一年墒情趋势”或“SNS00204333 近 90 天趋势”。",
            }
        if intent == "soil_severity_ranking" and requested_days > 365 and (
            slots.get("aggregation") in {"device", "province"} or slots.get("batch_devices") == "all"
        ):
            return {
                **result,
                "decision": "block",
                "allow_execute": False,
                "policy_decision": "block",
                "reason": "large_device_ranking_not_allowed",
                "violations": [
                    {"field": "time_range", "reason": "requested_days_exceed_limit", "requested_value": requested_days, "allowed_value": 365},
                    {"field": "aggregation", "reason": "large_scope_device_ranking_not_allowed", "requested_value": slots.get("aggregation")},
                ],
                "message": "当前不支持全省/全部设备的大时间窗排名。请缩小到具体地区，或改查最近 30 天、前 20 个设备。",
                "blocked": True,
                "block_message": "当前不支持全省/全部设备的大时间窗排名。请缩小到具体地区，或改查最近 30 天、前 20 个设备。",
            }
        if intent == "soil_severity_ranking" and top_n > 20:
            return {
                **result,
                "decision": "clarify",
                "allow_execute": False,
                "policy_decision": "clarify",
                "reason": "top_n_requires_confirmation",
                "violations": [{"field": "top_n", "reason": "requested_value_exceeded", "requested_value": top_n, "allowed_value": 20}],
                "message": "当前一次最多返回前 20 个结果。是否改查前 20 个最严重设备？",
                "must_clarify": True,
                "clarify_message": "当前一次最多返回前 20 个结果。是否改查前 20 个最严重设备？",
            }

        limit_map = {
            "soil_recent_summary": 90,
            "soil_region_query": 90,
            "soil_device_query": 90,
            "soil_anomaly_query": 180,
            "soil_severity_ranking": 365,
        }
        max_days = limit_map.get(intent)
        if max_days and requested_days > max_days:
            if intent == "soil_anomaly_query":
                # For anomaly questions we ask for confirmation instead of
                # silently shrinking because the omitted period can change the
                # user's risk interpretation.
                return {
                    **result,
                    "decision": "clarify",
                    "allow_execute": False,
                    "policy_decision": "clarify",
                    "resolved_days": max_days,
                    "reason": "time_window_requires_confirmation",
                    "violations": [{"field": "time_range", "reason": "requested_days_exceed_limit", "requested_value": requested_days, "allowed_value": max_days}],
                    "message": f"异常查询当前最多支持最近 {max_days} 天。请确认是否改查最近 {max_days} 天，或补充更小的地区/设备范围。",
                    "must_clarify": True,
                    "clarify_message": f"异常查询当前最多支持最近 {max_days} 天。请确认是否改查最近 {max_days} 天，或补充更小的地区/设备范围。",
                }
            effective_business_time = self._shrink_business_time(
                business_time=business_time,
                fallback_time_range=time_range,
                max_days=max_days,
            )
            return {
                **result,
                "decision": "shrink",
                "resolved_days": max_days,
                "reason": "time_window_shrunk",
                "violations": [{"field": "time_range", "reason": "requested_days_exceed_limit", "requested_value": requested_days, "allowed_value": max_days}],
                "message": f"当前已将时间范围收敛到最近 {max_days} 天内。",
                "shrink_applied": True,
                "effective_slots": dict(slots),
                "effective_business_time": effective_business_time,
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

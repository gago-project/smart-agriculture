from __future__ import annotations

"""Deterministic soil warning rule engine.

The rule engine is the business authority for drought, waterlogging, and device
fault judgments.  It uses configured thresholds from `RuleRepository` and never
depends on LLM output, so fact answers remain stable and explainable.
"""

from typing import Any

from app.repositories.rule_repository import RuleRepository

def _safe_float(value: Any) -> float | None:
    """Convert possibly-null database values into floats for rule checks."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_record_status(record: dict[str, Any], *, thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """Evaluate one soil record and return normalized warning fields."""
    thresholds = thresholds or {
        "heavy_drought_max": 50.0,
        "waterlogging_min": 150.0,
        "device_fault_water20": 0.0,
        "device_fault_t20": 0.0,
    }
    water20 = _safe_float(record.get("water20cm")) or 0.0
    t20 = _safe_float(record.get("t20cm")) or 0.0
    if water20 == thresholds["device_fault_water20"] and t20 == thresholds["device_fault_t20"]:
        return {
            "soil_status": "device_fault",
            "warning_level": "device_fault",
            "display_label": "设备故障",
            "soil_anomaly_score": 100.0,
        }
    if water20 < thresholds["heavy_drought_max"]:
        return {
            "soil_status": "heavy_drought",
            "warning_level": "heavy_drought",
            "display_label": "重旱",
            "soil_anomaly_score": round(90 + (thresholds["heavy_drought_max"] - water20), 2),
        }
    if water20 >= thresholds["waterlogging_min"]:
        return {
            "soil_status": "waterlogging",
            "warning_level": "waterlogging",
            "display_label": "涝渍",
            "soil_anomaly_score": round(80 + (water20 - thresholds["waterlogging_min"]), 2),
        }
    return {
        "soil_status": "not_triggered",
        "warning_level": "none",
        "display_label": "未达到预警条件",
        "soil_anomaly_score": round(max(0.0, 70 - abs(water20 - 85) / 2), 2),
    }


class SoilRuleEngineService:
    """Apply warning rules to query results and choose the next answer path."""

    def __init__(self, rule_repository: RuleRepository | None = None):
        """Rules are repository-backed so thresholds can be managed centrally."""
        self.rule_repository = rule_repository or RuleRepository()

    async def evaluate(self, *, intent: str, query_result: dict[str, Any], answer_type: str, slots: dict[str, Any]) -> dict[str, Any]:
        """Evaluate query records and route to template/advice/response nodes."""
        del intent
        records = query_result.get("records", [])
        rule_profile = await self.rule_repository.get_warning_rule_metadata()
        thresholds = {
            "heavy_drought_max": rule_profile["heavy_drought_max"],
            "waterlogging_min": rule_profile["waterlogging_min"],
            "device_fault_water20": rule_profile["device_fault_water20"],
            "device_fault_t20": rule_profile["device_fault_t20"],
        }
        evaluated_records = [{**record, **evaluate_record_status(record, thresholds=thresholds)} for record in records]
        route_action = "response_only"
        if answer_type == "soil_warning_answer":
            if slots.get("need_template") and slots.get("render_mode") == "plus_explanation":
                route_action = "template_and_advice"
            elif slots.get("need_template"):
                route_action = "template_only"
        elif answer_type == "soil_advice_answer":
            route_action = "advice_only"
        return {
            "rule_name": rule_profile["rule_name"],
            "route_action": route_action,
            "evaluated_records": evaluated_records,
        }


__all__ = ["SoilRuleEngineService", "evaluate_record_status"]

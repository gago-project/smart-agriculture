"""Shared warning predicate evaluation for deterministic soil queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WarningMatch:
    matched: bool
    warning_level: str | None = None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class WarningPredicateService:
    """Evaluate whether one raw soil record matches the active warning rule."""

    def evaluate(self, record: dict[str, Any], rule_row: dict[str, Any] | None) -> WarningMatch:
        rule_definition = (rule_row or {}).get("rule_definition_json") or {}
        if isinstance(rule_definition, str):
            try:
                rule_definition = json.loads(rule_definition)
            except json.JSONDecodeError:
                rule_definition = {}
        rules = list((rule_definition or {}).get("rules") or [])
        rules.sort(key=lambda item: int(item.get("priority") or 999))
        water20 = _safe_float(record.get("water20cm"))
        t20 = _safe_float(record.get("t20cm"))
        for item in rules:
            warning_level = str(item.get("warning_level") or "")
            condition = str(item.get("condition") or "")
            if warning_level == "device_fault" and water20 == 0 and t20 == 0:
                return WarningMatch(matched=True, warning_level=warning_level)
            if warning_level == "heavy_drought" and "<" in condition and water20 is not None:
                try:
                    if water20 < float(condition.split("<")[-1].strip()):
                        return WarningMatch(matched=True, warning_level=warning_level)
                except ValueError:
                    continue
            if warning_level == "waterlogging" and ">=" in condition and water20 is not None:
                try:
                    if water20 >= float(condition.split(">=")[-1].strip()):
                        return WarningMatch(matched=True, warning_level=warning_level)
                except ValueError:
                    continue
        return WarningMatch(matched=False, warning_level=None)

    def filter_records(
        self,
        records: list[dict[str, Any]],
        rule_row: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        return [record for record in records if self.evaluate(record, rule_row).matched]


__all__ = ["WarningMatch", "WarningPredicateService"]

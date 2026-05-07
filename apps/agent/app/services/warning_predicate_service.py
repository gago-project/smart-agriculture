"""Shared warning predicate evaluation for deterministic soil queries."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


_CONDITION_TOKEN_RE = re.compile(r"\s+(and|or)\s+", re.IGNORECASE)
_ATOMIC_CONDITION_RE = re.compile(
    r"^(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<operator><=|>=|!=|=|==|<|>)\s*(?P<literal>.+?)$"
)


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
    """Evaluate and render warning predicates from `metric_rule.rule_definition_json`."""

    def build_sql_predicate(
        self,
        *,
        rule_row: dict[str, Any] | None,
        warning_type: str | None,
        time_column: str,
    ) -> str:
        rule_definition = self._rule_definition(rule_row)
        fragments: list[str] = []
        for rule in self._ordered_rules(rule_definition):
            level = str(rule.get("warning_level") or "").strip()
            if warning_type and level != warning_type:
                continue
            predicate = self._rule_sql_predicate(
                rule=rule,
                rule_definition=rule_definition,
                time_column=time_column,
            )
            if predicate:
                fragments.append(predicate)
        if not fragments:
            return "0 = 1"
        if len(fragments) == 1:
            return fragments[0]
        return f"({' OR '.join(fragments)})"

    def build_warning_case_expression(
        self,
        *,
        rule_row: dict[str, Any] | None,
        time_column: str,
        default_label: str = "normal",
    ) -> str:
        rule_definition = self._rule_definition(rule_row)
        clauses = ["CASE"]
        for rule in self._ordered_rules(rule_definition):
            level = str(rule.get("warning_level") or "").strip()
            predicate = self._rule_sql_predicate(
                rule=rule,
                rule_definition=rule_definition,
                time_column=time_column,
            )
            if not level or not predicate:
                continue
            clauses.append(f" WHEN {predicate} THEN '{level}'")
        clauses.append(f" ELSE '{default_label}' END")
        return "".join(clauses)

    def evaluate(
        self,
        record: dict[str, Any],
        rule_row: dict[str, Any] | None,
        record_time: datetime | str | None = None,
    ) -> WarningMatch:
        rule_definition = self._rule_definition(rule_row)
        effective_time = self._coerce_datetime(record_time or record.get("create_time") or record.get("time"))
        for rule in self._ordered_rules(rule_definition):
            level = str(rule.get("warning_level") or "").strip()
            condition = str(rule.get("condition") or "").strip()
            if not level or not condition:
                continue
            if not self._is_warning_level_active(
                warning_level=level,
                rule_definition=rule_definition,
                record_time=effective_time,
            ):
                continue
            if self._evaluate_condition(record, condition):
                return WarningMatch(matched=True, warning_level=level)
        return WarningMatch(matched=False, warning_level=None)

    def filter_records(
        self,
        records: list[dict[str, Any]],
        rule_row: dict[str, Any] | None,
        *,
        warning_type: str | None = None,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for record in records:
            match = self.evaluate(record, rule_row, record.get("create_time") or record.get("time"))
            if not match.matched:
                continue
            if warning_type and match.warning_level != warning_type:
                continue
            filtered.append(record)
        return filtered

    @staticmethod
    def _rule_definition(rule_row: dict[str, Any] | None) -> dict[str, Any]:
        definition = (rule_row or {}).get("rule_definition_json") or {}
        if isinstance(definition, str):
            try:
                definition = json.loads(definition)
            except json.JSONDecodeError:
                definition = {}
        return definition if isinstance(definition, dict) else {}

    @staticmethod
    def _ordered_rules(rule_definition: dict[str, Any]) -> list[dict[str, Any]]:
        rules = list((rule_definition or {}).get("rules") or [])
        rules.sort(key=lambda item: int(item.get("priority") or 999))
        return rules

    def _rule_sql_predicate(
        self,
        *,
        rule: dict[str, Any],
        rule_definition: dict[str, Any],
        time_column: str,
    ) -> str:
        condition = self._normalize_sql_condition(str(rule.get("condition") or ""))
        if not condition:
            return ""
        level = str(rule.get("warning_level") or "").strip()
        inactive_sql = self._inactive_period_sql(
            warning_level=level,
            rule_definition=rule_definition,
            time_column=time_column,
        )
        if not inactive_sql:
            return condition
        return f"({condition} AND NOT ({inactive_sql}))"

    @staticmethod
    def _normalize_sql_condition(condition: str) -> str:
        normalized = re.sub(r"\s+", " ", str(condition or "").strip())
        if not normalized:
            return ""
        normalized = re.sub(r"\band\b", "AND", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bor\b", "OR", normalized, flags=re.IGNORECASE)
        normalized = normalized.replace("==", "=")
        return normalized

    def _inactive_period_sql(
        self,
        *,
        warning_level: str,
        rule_definition: dict[str, Any],
        time_column: str,
    ) -> str:
        periods: list[str] = []
        for override in (rule_definition.get("seasonal_overrides") or []):
            suspended = {str(item).strip() for item in (override.get("suspended_warning_levels") or [])}
            if warning_level not in suspended:
                continue
            period = override.get("period") or {}
            month_start = int(period.get("month_start") or 0)
            day_start = int(period.get("day_start") or 0)
            month_end = int(period.get("month_end") or 0)
            day_end = int(period.get("day_end") or 0)
            if min(month_start, day_start, month_end, day_end) <= 0:
                continue
            start_key = f"{month_start:02d}-{day_start:02d}"
            end_key = f"{month_end:02d}-{day_end:02d}"
            record_key = f"DATE_FORMAT({time_column}, '%m-%d')"
            if start_key <= end_key:
                periods.append(f"{record_key} BETWEEN '{start_key}' AND '{end_key}'")
            else:
                periods.append(f"({record_key} >= '{start_key}' OR {record_key} <= '{end_key}')")
        if not periods:
            return ""
        if len(periods) == 1:
            return periods[0]
        return f"({' OR '.join(periods)})"

    def _is_warning_level_active(
        self,
        *,
        warning_level: str,
        rule_definition: dict[str, Any],
        record_time: datetime | None,
    ) -> bool:
        if record_time is None:
            return True
        record_date = record_time.date()
        for override in (rule_definition.get("seasonal_overrides") or []):
            suspended = {str(item).strip() for item in (override.get("suspended_warning_levels") or [])}
            if warning_level not in suspended:
                continue
            period = override.get("period") or {}
            month_start = int(period.get("month_start") or 0)
            day_start = int(period.get("day_start") or 0)
            month_end = int(period.get("month_end") or 0)
            day_end = int(period.get("day_end") or 0)
            if min(month_start, day_start, month_end, day_end) <= 0:
                continue
            if self._date_in_period(
                record_date,
                month_start=month_start,
                day_start=day_start,
                month_end=month_end,
                day_end=day_end,
            ):
                return False
        return True

    @staticmethod
    def _date_in_period(
        value: date,
        *,
        month_start: int,
        day_start: int,
        month_end: int,
        day_end: int,
    ) -> bool:
        try:
            start = date(value.year, month_start, day_start)
            end = date(value.year, month_end, day_end)
        except ValueError:
            return False
        if start <= end:
            return start <= value <= end
        return value >= start or value <= end

    def _evaluate_condition(self, record: dict[str, Any], condition: str) -> bool:
        tokens = _CONDITION_TOKEN_RE.split(str(condition or "").strip())
        if not tokens:
            return False
        result = self._evaluate_atomic_condition(record, tokens[0])
        index = 1
        while index + 1 < len(tokens):
            operator = tokens[index].lower()
            rhs = self._evaluate_atomic_condition(record, tokens[index + 1])
            if operator == "and":
                result = result and rhs
            else:
                result = result or rhs
            index += 2
        return result

    def _evaluate_atomic_condition(self, record: dict[str, Any], token: str) -> bool:
        match = _ATOMIC_CONDITION_RE.match(str(token or "").strip())
        if not match:
            return False
        field = match.group("field")
        operator = match.group("operator")
        literal = self._parse_literal(match.group("literal"))
        value = record.get(field)

        numeric_literal = _safe_float(literal)
        numeric_value = _safe_float(value)
        if numeric_literal is not None and numeric_value is not None:
            return self._compare(numeric_value, numeric_literal, operator)
        return self._compare(str(value), str(literal), operator)

    @staticmethod
    def _parse_literal(value: str) -> Any:
        normalized = str(value or "").strip().strip("'").strip('"')
        numeric = _safe_float(normalized)
        if numeric is not None:
            return numeric
        return normalized

    @staticmethod
    def _compare(left: Any, right: Any, operator: str) -> bool:
        if operator in {"=", "=="}:
            return left == right
        if operator == "!=":
            return left != right
        if operator == "<":
            return left < right
        if operator == ">":
            return left > right
        if operator == "<=":
            return left <= right
        if operator == ">=":
            return left >= right
        return False

    @staticmethod
    def _coerce_datetime(value: datetime | str | None) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        for fmt, size in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
            try:
                return datetime.strptime(text[:size], fmt)
            except ValueError:
                continue
        return None


__all__ = ["WarningMatch", "WarningPredicateService"]

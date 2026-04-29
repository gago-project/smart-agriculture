"""Post-generation fact checks before final answer verification.

Checks (original, blocking):
1. Answer must not be empty.
2. Business answers must have tool evidence in query_result or tool_trace.
3. Key entities in answer_facts must appear in final_answer.
4. No-data contradiction: tool showed data but answer claims 无数据.

Checks (new, alert-only — log warnings, never block):
5. Numeric value consistency: water-content numbers in answer within tool result range ±0.5%.
6. Time window consistency: dates in answer fall within resolved time window.
7. Status/level consistency: soil status labels in answer exist in tool result status sets.
8. Rank ordinal consistency: "第N名" in answer maps to the correct entity in items[N-1].
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_BUSINESS_ANSWER_TYPES = {"soil_summary_answer", "soil_ranking_answer", "soil_detail_answer"}

_STATUS_LABELS = {
    "重旱": "heavy_drought",
    "干旱": "drought",
    "偏旱": "mild_drought",
    "适宜": "normal",
    "偏湿": "mild_wet",
    "涝渍": "waterlogging",
    "设备故障": "device_fault",
}

_NO_DATA_PATTERN = re.compile(r"(无数据|找不到|没有数据|查不到|不存在|暂无记录)", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"\b(\d{1,3}(?:\.\d{1,2})?)\s*%?")
_DATE_YMD = re.compile(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")
_DATE_MD = re.compile(r"(\d{1,2})月(\d{1,2})日")
_RANK_PATTERN = re.compile(r"第\s*(\d+)\s*[名位]")


class FactCheckService:
    """Validate generated answers against query/rule/template bundles."""

    def verify(
        self,
        *,
        answer_type: str,
        answer_bundle: Any,
        query_result: Any,
        tool_trace: list | None = None,
        answer_facts: dict | None = None,
        resolved_args: dict | None = None,
    ) -> dict[str, Any]:
        """Return whether the answer should retry, fallback, or proceed.

        resolved_args — the Parameter Resolver output (contains start_time, end_time,
        canonical city/county/sn). Used by alert-only evidence checks.
        """
        final_answer = str(answer_bundle.get("final_answer") or "").strip()
        if not final_answer:
            return {
                "failed": True,
                "need_retry": False,
                "fallback_answer": "当前回答未生成成功，已安全降级，请换一种问法重试。",
                "warnings": [],
            }

        # ── blocking checks ───────────────────────────────────────────────────

        if answer_type in _BUSINESS_ANSWER_TYPES:
            query_payload = _as_dict(query_result)
            entries = []
            if query_payload:
                entries = query_payload.get("entries") or []
            has_entries = bool(entries)
            has_trace = bool(tool_trace)
            if not has_entries and not has_trace:
                return {
                    "failed": True,
                    "need_retry": False,
                    "fallback_answer": "当前业务回答缺少真实数据支撑，已安全降级，请重新提问。",
                    "warnings": [],
                }

            facts = answer_facts or {}
            entity_name = str(facts.get("entity_name") or "").strip()
            if entity_name and entity_name not in final_answer:
                return {
                    "failed": True,
                    "need_retry": True,
                    "fallback_answer": f"回答未提及目标对象「{entity_name}」，已安全降级，请重新提问。",
                    "warnings": [],
                }

            has_data = _tool_reported_data(facts, entries)
            if has_data and _answer_claims_no_data(final_answer):
                return {
                    "failed": True,
                    "need_retry": True,
                    "fallback_answer": "上一版回答与真实查询结果冲突：当前时间窗内存在真实数据，已安全降级，请重新提问。",
                    "warnings": [],
                }

        # ── alert-only evidence checks ────────────────────────────────────────

        warnings: list[str] = []
        rargs = resolved_args or {}
        qt = _as_dict(query_result)

        _check_numeric_values(final_answer, qt, tool_trace or [], warnings)
        _check_time_window(final_answer, rargs, warnings)
        _check_status_labels(final_answer, qt, tool_trace or [], warnings)
        _check_rank_ordinals(final_answer, qt, tool_trace or [], warnings)

        if warnings:
            logger.warning("FactCheck alert-mode warnings: %s", warnings)

        return {"failed": False, "need_retry": False, "fallback_answer": "", "warnings": warnings}


# ── alert check implementations ───────────────────────────────────────────────

def _as_dict(result: Any) -> dict:
    if isinstance(result, dict):
        return result
    model_dump = getattr(result, "model_dump", None)
    if callable(model_dump):
        payload = model_dump(exclude_none=True)
        return payload if isinstance(payload, dict) else {}
    return {}

def _collect_water_values(qt: dict, tool_trace: list) -> list[float]:
    """Gather all water-content numeric values from tool results."""
    values: list[float] = []

    def _from_result(result: Any) -> None:
        payload = _as_dict(result)
        for key in ("avg_water20cm",):
            v = payload.get(key)
            if v is not None:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass
        for rec in payload.get("alert_records") or []:
            for wk in ("water20cm", "water40cm", "water60cm", "water80cm"):
                v = rec.get(wk)
                if v is not None:
                    try:
                        values.append(float(v))
                    except (TypeError, ValueError):
                        pass
        latest = payload.get("latest_record") or {}
        for wk in ("water20cm", "water40cm", "water60cm", "water80cm"):
            v = latest.get(wk)
            if v is not None:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass
        for item in payload.get("items") or []:
            v = item.get("avg_water20cm")
            if v is not None:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass

    _from_result(qt)
    for entry in tool_trace:
        result = entry.get("result", {}) if isinstance(entry, dict) else {}
        if isinstance(result, dict):
            _from_result(result)

    return values


def _check_numeric_values(
    final_answer: str,
    qt: dict,
    tool_trace: list,
    warnings: list[str],
) -> None:
    water_values = _collect_water_values(qt, tool_trace)
    if not water_values:
        return
    lo = min(water_values) * (1 - 0.005)
    hi = max(water_values) * (1 + 0.005)
    # Only inspect numbers that look like percentages (0–100 range)
    candidates = [float(m) for m in _NUMBER_PATTERN.findall(final_answer) if 0 <= float(m) <= 100]
    for num in candidates:
        if num < lo or num > hi:
            warnings.append(
                f"数值核验: 回答中的 {num} 不在工具结果数值范围 [{lo:.2f}, {hi:.2f}] 内（±0.5% 容差）"
            )


def _check_time_window(final_answer: str, rargs: dict, warnings: list[str]) -> None:
    start_str = rargs.get("start_time")
    end_str = rargs.get("end_time")
    if not start_str or not end_str:
        return
    try:
        t_start = datetime.strptime(start_str[:10], "%Y-%m-%d")
        t_end = datetime.strptime(end_str[:10], "%Y-%m-%d")
    except ValueError:
        return

    mentioned_dates: list[datetime] = []
    for m in _DATE_YMD.findall(final_answer):
        try:
            mentioned_dates.append(datetime.strptime(m.replace("/", "-"), "%Y-%m-%d"))
        except ValueError:
            pass
    # For month-day patterns, use the year from t_start
    for m in _DATE_MD.finditer(final_answer):
        try:
            mentioned_dates.append(datetime(t_start.year, int(m.group(1)), int(m.group(2))))
        except ValueError:
            pass

    for dt in mentioned_dates:
        if not (t_start <= dt <= t_end):
            warnings.append(
                f"时间核验: 回答中的日期 {dt.strftime('%Y-%m-%d')} 不在查询时间窗 "
                f"{start_str[:10]} ~ {end_str[:10]} 内"
            )


def _collect_status_set(qt: dict, tool_trace: list) -> set[str]:
    statuses: set[str] = set()

    def _from_result(result: Any) -> None:
        payload = _as_dict(result)
        for k in payload.get("status_counts") or {}:
            statuses.add(k)
        for rec in payload.get("alert_records") or []:
            s = rec.get("soil_status")
            if s:
                statuses.add(s)
        latest = payload.get("latest_record") or {}
        s = latest.get("soil_status")
        if s:
            statuses.add(s)
        for item in payload.get("items") or []:
            s = item.get("status")
            if s:
                statuses.add(s)
        for k in (payload.get("status_summary") or {}):
            statuses.add(k)

    _from_result(qt)
    for entry in tool_trace:
        result = entry.get("result", {}) if isinstance(entry, dict) else {}
        if isinstance(result, dict):
            _from_result(result)

    return statuses


def _check_status_labels(
    final_answer: str,
    qt: dict,
    tool_trace: list,
    warnings: list[str],
) -> None:
    status_set = _collect_status_set(qt, tool_trace)
    if not status_set:
        return
    for label, code in _STATUS_LABELS.items():
        if label in final_answer and code not in status_set:
            warnings.append(
                f"状态核验: 回答中提到「{label}」({code})，但工具结果中无该状态记录"
            )


def _collect_items(qt: dict, tool_trace: list) -> list[dict]:
    items = _as_dict(qt).get("items") or []
    if items:
        return items
    for entry in tool_trace:
        result = _as_dict(entry.get("result", {}) if isinstance(entry, dict) else {})
        if result.get("items"):
            return result["items"]
    return []


def _check_rank_ordinals(
    final_answer: str,
    qt: dict,
    tool_trace: list,
    warnings: list[str],
) -> None:
    items = _collect_items(qt, tool_trace)
    if not items:
        return
    for m in _RANK_PATTERN.finditer(final_answer):
        rank = int(m.group(1))
        if rank < 1 or rank > len(items):
            continue
        item = items[rank - 1]
        name = str(item.get("name") or "")
        if name and name not in final_answer:
            warnings.append(
                f"排名核验: 回答中第{rank}名对应实体应为「{name}」，但未在回答中找到"
            )


# ── helpers ───────────────────────────────────────────────────────────────────

def _tool_reported_data(facts: dict, entries: list) -> bool:
    if facts.get("total_records", 0) > 0:
        return True
    if facts.get("record_count", 0) > 0:
        return True
    if facts.get("items"):
        return True
    for entry in entries:
        result = _as_dict(entry.get("result", {}) if isinstance(entry, dict) else {})
        if result.get("total_records", 0) > 0:
            return True
        if result.get("record_count", 0) > 0:
            return True
        if result.get("items"):
            return True
    return False


def _answer_claims_no_data(text: str) -> bool:
    return bool(_NO_DATA_PATTERN.search(text))


__all__ = ["FactCheckService"]

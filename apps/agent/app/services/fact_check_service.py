"""Post-generation fact checks before final answer verification.

Checks:
1. Answer must not be empty.
2. Business answers (soil_*_answer) must have tool evidence in query_result or tool_trace.
3. Key entities in answer_facts must appear in final_answer (name consistency).
4. Numeric claims: answer must not assert zero-data results when tool evidence shows data.
"""

from __future__ import annotations

import re
from typing import Any

_BUSINESS_ANSWER_TYPES = {"soil_summary_answer", "soil_ranking_answer", "soil_detail_answer"}


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
    ) -> dict[str, Any]:
        """Return whether the answer should retry, fallback, or proceed."""
        final_answer = str(answer_bundle.get("final_answer") or "").strip()
        if not final_answer:
            return {
                "failed": True,
                "need_retry": False,
                "fallback_answer": "当前回答未生成成功，已安全降级，请换一种问法重试。",
            }

        # Business answers require evidence from at least one tool call
        if answer_type in _BUSINESS_ANSWER_TYPES:
            entries = []
            if hasattr(query_result, "get"):
                entries = query_result.get("entries") or []
            has_entries = bool(entries)
            has_trace = bool(tool_trace)
            if not has_entries and not has_trace:
                return {
                    "failed": True,
                    "need_retry": False,
                    "fallback_answer": "当前业务回答缺少真实数据支撑，已安全降级，请重新提问。",
                }

            # Entity name consistency: if answer_facts names an entity, it should appear in the answer
            facts = answer_facts or {}
            entity_name = str(facts.get("entity_name") or "").strip()
            if entity_name and entity_name not in final_answer:
                return {
                    "failed": True,
                    "need_retry": True,
                    "fallback_answer": f"回答未提及目标对象「{entity_name}」，已安全降级，请重新提问。",
                }

            # No-data contradiction: tool reported data but answer says "无数据" / "找不到"
            has_data = _tool_reported_data(facts, entries)
            if has_data and _answer_claims_no_data(final_answer):
                return {
                    "failed": True,
                    "need_retry": True,
                    "fallback_answer": "回答声称无数据，但查询结果中存在数据，已安全降级，请重新提问。",
                }

        return {"failed": False, "need_retry": False, "fallback_answer": ""}


def _tool_reported_data(facts: dict, entries: list) -> bool:
    """Return True if the tool evidence contains actual records."""
    if facts.get("total_records", 0) > 0:
        return True
    if facts.get("record_count", 0) > 0:
        return True
    if facts.get("items"):
        return True
    for entry in entries:
        result = entry.get("result", {}) if isinstance(entry, dict) else {}
        if result.get("total_records", 0) > 0:
            return True
        if result.get("record_count", 0) > 0:
            return True
        if result.get("items"):
            return True
    return False


_NO_DATA_PATTERN = re.compile(r"(无数据|找不到|没有数据|查不到|不存在|暂无记录)", re.IGNORECASE)


def _answer_claims_no_data(text: str) -> bool:
    return bool(_NO_DATA_PATTERN.search(text))


__all__ = ["FactCheckService"]

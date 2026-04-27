"""Post-generation fact checks before final answer verification.

Checks:
1. Answer must not be empty.
2. Business answers (soil_*_answer) must have tool evidence in query_result or tool_trace.
"""

from __future__ import annotations

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
            has_records = bool(query_result.get("records") if hasattr(query_result, "get") else [])
            has_trace = bool(tool_trace)
            if not has_records and not has_trace:
                return {
                    "failed": True,
                    "need_retry": False,
                    "fallback_answer": "当前业务回答缺少真实数据支撑，已安全降级，请重新提问。",
                }

        return {"failed": False, "need_retry": False, "fallback_answer": ""}


__all__ = ["FactCheckService"]

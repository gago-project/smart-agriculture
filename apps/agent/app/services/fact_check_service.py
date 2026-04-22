"""Post-generation fact checks before final answer verification.

This service catches obvious mismatches between generated text and structured
facts.  It is deliberately small today, but it is the right extension point for
future checks such as count consistency, device identity consistency, and
template field completeness.
"""

from __future__ import annotations


from typing import Any


class FactCheckService:
    """Validate generated answers against query/rule/template bundles."""

    def verify(
        self,
        *,
        answer_type: str,
        answer_bundle: dict[str, Any],
        query_result: dict[str, Any],
        rule_result: dict[str, Any],
        template_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Return whether the answer should retry, fallback, or proceed."""
        final_answer = str(answer_bundle.get("final_answer") or "").strip()
        if not final_answer:
            return {
                "failed": True,
                "need_retry": False,
                "fallback_answer": "当前回答未生成成功，已安全降级，请换一种问法重试。",
            }
        if answer_type == "soil_warning_answer" and template_result.get("render_mode") == "strict":
            records = rule_result.get("evaluated_records") or query_result.get("records") or []
            if records and records[0].get("device_sn") not in final_answer:
                return {
                    "failed": False,
                    "need_retry": True,
                    "fallback_answer": "当前模板校验未通过，已安全降级。",
                }
        return {"failed": False, "need_retry": False, "fallback_answer": ""}


__all__ = ["FactCheckService"]

from __future__ import annotations

"""Final answer verifier for the restricted Flow.

`FactCheckService` validates consistency against data.  This service performs
the final product-level sanity check before `verified_end`, such as ensuring
clarification answers actually ask the user to provide missing information.
"""

from typing import Any


class AnswerVerifyService:
    """Accept or reject the final answer bundle."""

    def verify(self, *, answer_type: str, answer_bundle: dict[str, Any]) -> dict[str, Any]:
        """Return fallback text when the answer is empty or malformed."""
        final_answer = str(answer_bundle.get("final_answer") or "").strip()
        if not final_answer:
            return {"failed": True, "fallback_answer": "当前无法给出稳定回答，请换个问法重试。"}
        if answer_type == "clarification_answer" and "可以" not in final_answer and "补充" not in final_answer:
            return {"failed": True, "fallback_answer": "请补充地区、设备或时间范围，例如：如东县最近怎么样。"}
        return {"failed": False, "fallback_answer": ""}


__all__ = ["AnswerVerifyService"]

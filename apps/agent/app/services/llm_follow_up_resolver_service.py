"""Optional low-cost LLM fallback for uncertain follow-up resolution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是土壤墒情 chat-v2 的上下文追问解析器，只输出 JSON，不解释。

任务：判断当前输入是否承接上一轮数据查询上下文。

严格输出：
{
  "is_follow_up": true,
  "operation": "standalone|inherit|replace_slot|correct_slot|switch_capability|subset|drilldown_ref|clarify",
  "new_slots": {},
  "inherit_slots": [],
  "confidence": 0.0
}

要求：
- 只判断是否承接上文，不生成最终答案
- 如果像“那海安市呢”“最近一个月”“不是如东县，是如皋市”，应视作 follow-up
- 如果当前输入本身就是完整独立查询，返回 is_follow_up=false, operation=standalone
"""

_VALID_OPERATIONS = {
    "standalone",
    "inherit",
    "replace_slot",
    "correct_slot",
    "switch_capability",
    "subset",
    "drilldown_ref",
    "clarify",
}


@dataclass(frozen=True)
class LlmFollowUpResolution:
    is_follow_up: bool
    operation: str
    new_slots: dict[str, Any] = field(default_factory=dict)
    inherit_slots: list[str] = field(default_factory=list)
    confidence: float = 0.0


class LlmFollowUpResolverService:
    """Use a bounded LLM call to resolve uncertain follow-up semantics."""

    def __init__(self, qwen_client: Any = None, timeout_seconds: float = 3.0) -> None:
        self._client = qwen_client
        self._timeout = timeout_seconds

    async def resolve(self, *, text: str, context: dict[str, Any], latest_target: dict[str, Any] | None) -> LlmFollowUpResolution | None:
        normalized = str(text or "").strip()
        if not normalized:
            return None
        if not self._client or not getattr(self._client, "available", lambda: False)():
            logger.debug("LLM follow-up resolver unavailable; falling back to deterministic path")
            return None

        payload = {
            "text": normalized,
            "latest_target": latest_target or {},
            "context_version": context.get("context_version"),
        }
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": str(payload)},
        ]
        try:
            raw = await asyncio.wait_for(self._client._request_json(messages=messages), timeout=self._timeout)
        except Exception as exc:
            logger.debug("LLM follow-up resolver fallback (timeout/error): %s", exc)
            return None

        if not isinstance(raw, dict):
            logger.debug("LLM follow-up resolver fallback (non-dict payload)")
            return None

        operation = str(raw.get("operation") or "").strip()
        if operation not in _VALID_OPERATIONS:
            logger.debug("LLM follow-up resolver fallback (invalid operation): %r", raw)
            return None

        try:
            confidence = float(raw.get("confidence"))
        except (TypeError, ValueError):
            logger.debug("LLM follow-up resolver fallback (invalid confidence): %r", raw.get("confidence"))
            return None

        inherit_slots = raw.get("inherit_slots")
        new_slots = raw.get("new_slots")
        if not isinstance(inherit_slots, list) or not isinstance(new_slots, dict):
            logger.debug("LLM follow-up resolver fallback (invalid slot payload): %r", raw)
            return None

        return LlmFollowUpResolution(
            is_follow_up=bool(raw.get("is_follow_up")),
            operation=operation,
            new_slots=new_slots,
            inherit_slots=[str(item) for item in inherit_slots],
            confidence=max(0.0, min(1.0, confidence)),
        )


__all__ = ["LlmFollowUpResolverService", "LlmFollowUpResolution"]

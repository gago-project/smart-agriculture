"""Semantic parser: coreference resolution + intent extraction in one LLM call.

Invoked only when InputGuard returns business_colloquial (low rule confidence)
or when coreference markers are detected ("它", "那个", "换成上周"…).

One LLM call serves three purposes (P1-7 / P1-8 / P1-9):
  - InputGuard LLM fallback: reclassify ambiguous inputs
  - Coreference resolution: expand "它"/"那个地区" to concrete entities
  - Intent extraction: return explicit intent_hint for AgentLoopNode

Timeout: 3 s — on any failure the raw user_input is returned unchanged
(宁可多查一次，不拦截合法请求).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是土壤墒情Agent的语义解析器，只输出JSON，不解释。

任务：
1. 将用户输入中的代词（它、那个地区、那个设备、换成上周 等）替换为对话历史中已明确的实体或时间，输出为 resolved_input。
2. 识别用户意图：soil_summary（整体概览）/ soil_ranking（排名）/ soil_detail（某地/设备详情）/ unclear。
3. 提取实体：city、county、sn（如有）。
4. 提取时间枚举（如有）：today / yesterday / last_3_days / last_7_days / last_14_days / last_30_days / last_week / this_month / last_month。
5. 若信息严重缺失无法推断，needs_clarify=true，clarify_message 说明缺少什么。

输出格式（严格 JSON，所有字段都要存在）：
{
  "resolved_input": "展开代词后的完整问题，如无代词则与原文相同",
  "intent_hint": "soil_summary|soil_ranking|soil_detail|unclear",
  "entities": {"city": "...", "county": "...", "sn": "..."},
  "time_hint": "last_7_days|...|null",
  "needs_clarify": false,
  "clarify_message": ""
}
"""

_VALID_INTENT_HINTS = {"soil_summary", "soil_ranking", "soil_detail", "unclear"}
_VALID_TIME_HINTS = {
    "today", "yesterday", "last_3_days", "last_7_days",
    "last_14_days", "last_30_days", "last_week", "this_month", "last_month",
}


@dataclass
class SemanticParseResult:
    """Structured output from one SemanticParserService call."""

    resolved_input: str
    intent_hint: str = "unclear"
    entities: dict[str, str] = field(default_factory=dict)
    time_hint: str | None = None
    needs_clarify: bool = False
    clarify_message: str = ""


def _fallback(user_input: str) -> SemanticParseResult:
    """Return a pass-through result when the LLM is unavailable or fails."""
    return SemanticParseResult(resolved_input=user_input)


class SemanticParserService:
    """One-shot LLM call that resolves coreferences and extracts structured intent."""

    def __init__(self, qwen_client: Any = None, timeout_seconds: float = 3.0) -> None:
        self._client = qwen_client
        self._timeout = timeout_seconds

    async def parse(
        self,
        user_input: str,
        history_tail: list[dict[str, Any]],
    ) -> SemanticParseResult:
        """Parse user_input with optional history context.

        history_tail: last few messages from SessionContextRepository (at most 6
        messages = ~3 turns) — passed verbatim as user/assistant pairs.
        Falls back to raw user_input on any error or timeout.
        """
        if not self._client or not getattr(self._client, "available", lambda: False)():
            return _fallback(user_input)

        # Build a compact history snippet (most recent 6 messages)
        recent = history_tail[-6:] if len(history_tail) > 6 else history_tail
        history_text = "\n".join(
            f"[{m['role']}]: {m.get('content') or ''}"
            for m in recent
            if m.get("role") in ("user", "assistant") and m.get("content")
        )

        user_msg = (
            f"对话历史（最近几轮）：\n{history_text}\n\n当前用户输入：{user_input}"
            if history_text
            else f"当前用户输入：{user_input}"
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        import asyncio
        try:
            raw = await asyncio.wait_for(
                self._client._request_json(messages=messages),
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.debug("SemanticParser fallback (timeout/error): %s", exc)
            return _fallback(user_input)

        if not isinstance(raw, dict):
            return _fallback(user_input)

        try:
            resolved_input = str(raw.get("resolved_input") or user_input).strip() or user_input
            intent_hint = str(raw.get("intent_hint") or "unclear")
            if intent_hint not in _VALID_INTENT_HINTS:
                intent_hint = "unclear"

            entities_raw = raw.get("entities") or {}
            entities = {
                k: str(v).strip()
                for k, v in entities_raw.items()
                if v and str(v).strip()
            }

            time_hint = raw.get("time_hint")
            if time_hint not in _VALID_TIME_HINTS:
                time_hint = None

            needs_clarify = bool(raw.get("needs_clarify"))
            clarify_message = str(raw.get("clarify_message") or "").strip()

            return SemanticParseResult(
                resolved_input=resolved_input,
                intent_hint=intent_hint,
                entities=entities,
                time_hint=time_hint,
                needs_clarify=needs_clarify,
                clarify_message=clarify_message,
            )
        except Exception as exc:
            logger.debug("SemanticParser parse error: %s", exc)
            return _fallback(user_input)


__all__ = ["SemanticParserService", "SemanticParseResult"]

"""LLM fallback guard for low-confidence inputs in chat-v2.

When rule-based InputGuardService cannot confidently classify an input,
this service makes a bounded LLM call that returns one of four categories:
  greeting           → fixed greeting template
  capability_question → fixed capability template
  out_of_domain      → fixed invalid/boundary template
  allow              → proceed to business flow
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是土壤墒情问答系统的输入分类器，只输出 JSON，不解释。

任务：判断当前用户输入属于哪种类型：
- greeting：问候语或寒暄（你好、在吗、嗨、早上好、哈哈等）
- capability_question：询问系统功能或能力范围（你能做什么、有哪些功能、你支持什么等）
- out_of_domain：与土壤墒情无关的废话、闲聊、离题内容、生活问题、商品问题等
- allow：看起来像墒情业务问题，或存在明显墒情查询意图，应继续处理

严格输出：
{
  "category": "greeting|capability_question|out_of_domain|allow",
  "confidence": 0.0
}

规则：
- 明显涉及墒情、预警、异常、设备、点位、地区、时间范围查询 → allow
- 问候语、寒暄短句 → greeting
- 询问系统功能或支持范围 → capability_question
- 其余与墒情无关的输入 → out_of_domain
- confidence 取 0 到 1 之间的小数，对把握度高的情况给出接近 1 的值
"""

_VALID_CATEGORIES = {"greeting", "capability_question", "out_of_domain", "allow"}


@dataclass(frozen=True)
class LlmInputGuardResult:
    category: str = "allow"
    confidence: float = 0.0


class LlmInputGuardService:
    """Use a bounded LLM call to classify low-confidence inputs into 4 categories."""

    def __init__(self, qwen_client: Any = None, timeout_seconds: float = 3.0) -> None:
        self._client = qwen_client
        self._timeout = timeout_seconds

    async def classify(self, text: str) -> LlmInputGuardResult:
        normalized = str(text or "").strip()
        if not normalized:
            return LlmInputGuardResult()
        if not self._client or not getattr(self._client, "available", lambda: False)():
            logger.debug("LLM input guard unavailable; falling back to allow")
            return LlmInputGuardResult()

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": normalized},
        ]
        try:
            raw = await asyncio.wait_for(
                self._client._request_json(messages=messages),
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.debug("LLM input guard fallback (timeout/error): %s", exc)
            return LlmInputGuardResult()

        if not isinstance(raw, dict):
            logger.debug("LLM input guard fallback (non-dict payload)")
            return LlmInputGuardResult()

        category = str(raw.get("category") or "").strip()
        confidence_raw = raw.get("confidence")
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            logger.debug("LLM input guard fallback (invalid confidence): %r", confidence_raw)
            return LlmInputGuardResult()

        if category not in _VALID_CATEGORIES:
            logger.debug("LLM input guard fallback (invalid category): %r", raw)
            return LlmInputGuardResult()

        return LlmInputGuardResult(
            category=category,
            confidence=max(0.0, min(1.0, confidence)),
        )


__all__ = ["LlmInputGuardService", "LlmInputGuardResult"]

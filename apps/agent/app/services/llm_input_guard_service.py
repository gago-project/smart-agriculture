"""LLM fallback guard for low-confidence non-business inputs in chat-v2."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是土壤墒情问答系统的输入守卫，只输出 JSON，不解释。

任务：判断当前输入是否应该继续进入墒情业务问答。
- allow：看起来像墒情业务问题，或存在明显业务意图
- intercept：看起来是废话、闲聊、离题内容、生活问题、商品名词、支付消费问题等，不应进入墒情业务问答

严格输出：
{
  "decision": "allow|intercept",
  "reason": "noise|off_topic",
  "confidence": 0.0
}

规则：
- 如果输入明显涉及墒情、预警、异常、设备、点位、地区、时间范围查询，返回 allow
- 如果输入像“上岛咖啡京东卡”“今天午饭吃什么”“京东卡可以提现吗”这类非墒情内容，返回 intercept
- confidence 取 0 到 1 之间的小数
"""

_VALID_DECISIONS = {"allow", "intercept"}
_VALID_REASONS = {"noise", "off_topic"}


@dataclass(frozen=True)
class LlmInputGuardResult:
    decision: str = "allow"
    reason: str = "noise"
    confidence: float = 0.0


class LlmInputGuardService:
    """Use a bounded LLM call to classify low-confidence non-business inputs."""

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

        decision = str(raw.get("decision") or "").strip()
        reason = str(raw.get("reason") or "").strip()
        confidence_raw = raw.get("confidence")
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            logger.debug("LLM input guard fallback (invalid confidence): %r", confidence_raw)
            return LlmInputGuardResult()

        if decision not in _VALID_DECISIONS or reason not in _VALID_REASONS:
            logger.debug("LLM input guard fallback (invalid decision payload): %r", raw)
            return LlmInputGuardResult()

        bounded_confidence = max(0.0, min(1.0, confidence))
        return LlmInputGuardResult(
            decision=decision,
            reason=reason,
            confidence=bounded_confidence,
        )


__all__ = ["LlmInputGuardService", "LlmInputGuardResult"]

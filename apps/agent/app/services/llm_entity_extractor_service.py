"""LLM fallback for entity extraction when alias matching finds nothing.

Triggered only when the alias table produces no city/county/SN match AND
the input contains a domain signal. LLM output is validated against the
alias table before use — unknown names are discarded to prevent hallucination.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.7

_SYSTEM_PROMPT = """\
你是土壤墒情系统的地区实体提取器，只输出 JSON，不解释。

从用户输入中提取地区名称和设备编号。

严格输出：
{
  "city": "市名称或 null",
  "county": "县区名称或 null",
  "sn": "设备编号如 SNS00204333 或 null",
  "confidence": 0.0
}

规则：
- 只提取明确出现在文本中的实体，不推断、不猜测
- city 填完整市名（如"南通市"），没有则填 null
- county 填完整县区名（如"海门区"），没有则填 null
- sn 格式为 SNS + 8位数字，没有则填 null
- confidence 为 0 到 1 之间的小数，确定时给接近 1 的值
- 找不到任何实体时，所有字段填 null，confidence 填 0
"""


@dataclass(frozen=True)
class LlmEntityExtraction:
    city: str | None = None
    county: str | None = None
    sn: str | None = None
    confidence: float = 0.0


class LlmEntityExtractorService:
    """Use a bounded LLM call to extract region entities from colloquial input."""

    def __init__(self, qwen_client: Any = None, timeout_seconds: float = 2.0) -> None:
        self._client = qwen_client
        self._timeout = timeout_seconds

    async def extract(self, text: str) -> LlmEntityExtraction | None:
        normalized = str(text or "").strip()
        if not normalized:
            return None
        if not self._client or not getattr(self._client, "available", lambda: False)():
            logger.debug("LLM entity extractor unavailable; skipping")
            return None

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
            logger.debug("LLM entity extractor fallback (timeout/error): %s", exc)
            return None

        if not isinstance(raw, dict):
            return None

        city = str(raw.get("city") or "").strip() or None
        county = str(raw.get("county") or "").strip() or None
        sn = str(raw.get("sn") or "").strip() or None
        try:
            confidence = float(raw.get("confidence") or 0.0)
        except (TypeError, ValueError):
            return None

        confidence = max(0.0, min(1.0, confidence))
        if confidence < _CONFIDENCE_THRESHOLD:
            logger.debug("LLM entity extractor low confidence=%.2f; discarding", confidence)
            return None

        return LlmEntityExtraction(city=city, county=county, sn=sn, confidence=confidence)


__all__ = ["LlmEntityExtractorService", "LlmEntityExtraction"]

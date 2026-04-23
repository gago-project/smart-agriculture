"""Minimal Qwen/DashScope client used by the restricted Agent Flow.

Qwen is optional and bounded.  It can help parse intent/slots or polish a
deterministic answer, but all calls require JSON output and failures return
`None` so deterministic local behavior remains available without an API key.
"""

from __future__ import annotations


from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
from typing import Any


DEFAULT_QWEN_MODEL = "qwen-max"


class QwenClient:
    """HTTP client for Qwen's OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        api_key: str = "",
        *,
        model: str = DEFAULT_QWEN_MODEL,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        timeout_seconds: float = 20.0,
    ) -> None:
        """Store model/client configuration; no request is made at construction."""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def available(self) -> bool:
        """Return whether the client can make authenticated Qwen calls."""
        return bool(self.api_key)

    async def extract_intent_slots(self, *, user_input: str, session_id: str) -> dict[str, Any] | None:
        """Ask Qwen for structured intent/slot JSON."""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是土壤墒情智能体的受限解析器。"
                    "只输出 JSON，字段包含 intent、answer_type、slots。"
                ),
            },
            {"role": "user", "content": f"session_id={session_id}\nuser_input={user_input}"},
        ]
        return await self._request_json(messages=messages)

    async def generate_controlled_answer(self, *, facts: dict[str, Any], fallback_answer: str, answer_type: str) -> str | None:
        """Ask Qwen to rewrite only the supplied deterministic facts."""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是土壤墒情智能体的受控生成器。"
                    "只能基于给定 facts 重写回答，不允许新增事实。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "answer_type": answer_type,
                        "facts": self._json_ready(facts),
                        "fallback_answer": fallback_answer,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        response = await self._request_json(messages=messages)
        if not response:
            return None
        answer = response.get("final_answer")
        return answer if isinstance(answer, str) and answer.strip() else None

    async def _request_json(self, *, messages: list[dict[str, str]]) -> dict[str, Any] | None:
        """Execute a JSON-mode request and return parsed JSON or `None`."""
        if not self.available():
            return None
        try:
            import httpx
        except Exception:
            return None

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                # The Authorization header is constructed here only; callers
                # should never log or persist the configured API key.
                response = await client.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if isinstance(content, dict):
                    return content
                return json.loads(content)
        except Exception:
            return None

    def _json_ready(self, value: Any) -> Any:
        """Convert nested Pydantic/enum/datetime values into JSON-safe data."""
        if hasattr(value, "model_dump"):
            return self._json_ready(value.model_dump(exclude_none=True))
        if isinstance(value, dict):
            return {key: self._json_ready(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_ready(item) for item in value]
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat(timespec="seconds")
        return value

"""Minimal Qwen/DashScope client used by the restricted Agent Flow.

Qwen is optional and bounded.  It can help parse intent/slots or polish a
deterministic answer, but all calls require JSON output and failures return
`None` so deterministic local behavior remains available without an API key.

P2-16: When the primary model fails (HTTP error / timeout / empty response),
the client automatically retries once with a fallback model. The fallback
list is configurable via `fallback_models` and defaults to ["qwen-turbo"].
"""

from __future__ import annotations


import logging
import os
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
from typing import Any


logger = logging.getLogger(__name__)


DEFAULT_QWEN_MODEL = "qwen-max"
DEFAULT_FALLBACK_MODELS = ["qwen-turbo"]


class QwenClient:
    """HTTP client for Qwen's OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        api_key: str = "",
        *,
        model: str = DEFAULT_QWEN_MODEL,
        fallback_models: list[str] | None = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        timeout_seconds: float = 20.0,
    ) -> None:
        """Store model/client configuration; no request is made at construction.

        fallback_models: ordered list of backup model names to try on primary failure.
        Set QWEN_FALLBACK_MODELS env (comma-separated) to override default.
        """
        self.api_key = api_key
        self.model = model
        env_fallback = os.getenv("QWEN_FALLBACK_MODELS", "")
        if fallback_models is None and env_fallback:
            fallback_models = [m.strip() for m in env_fallback.split(",") if m.strip()]
        self.fallback_models = fallback_models if fallback_models is not None else list(DEFAULT_FALLBACK_MODELS)
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

    async def call_with_tools(
        self,
        *,
        messages: list[dict],
        tools: list[dict],
    ) -> dict | None:
        """Call Qwen with function calling tools, with automatic backup model fallback.

        Tries the primary model first; on any failure (HTTP error, timeout,
        unparseable response) attempts each fallback model in order. Returns
        None only when all models fail.

        Returns one of:
        - {"type": "tool_calls", "calls": [...], "model_used": str}
        - {"type": "text", "content": str, "model_used": str}
        - None  (LLM unavailable or all models failed)
        """
        if not self.available():
            return None

        candidate_models = [self.model, *self.fallback_models]
        last_error: Exception | None = None
        for idx, model_name in enumerate(candidate_models):
            try:
                result = await self._call_with_tools_single(
                    messages=messages, tools=tools, model_name=model_name
                )
            except Exception as exc:
                last_error = exc
                logger.warning("LLM call failed on model=%s (attempt %d): %s", model_name, idx + 1, exc)
                continue
            if result is not None:
                if idx > 0:
                    logger.info("LLM fell back from %s to %s", self.model, model_name)
                return {**result, "model_used": model_name}
        if last_error:
            logger.error("All LLM models failed; last error: %s", last_error)
        return None

    async def _call_with_tools_single(
        self,
        *,
        messages: list[dict],
        tools: list[dict],
        model_name: str,
    ) -> dict | None:
        """Single model attempt for call_with_tools. Raises on transport error."""
        try:
            import httpx
            import json as _json
        except Exception:
            return None

        payload = {
            "model": model_name,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.1,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]

        tool_calls = message.get("tool_calls")
        if tool_calls:
            parsed: list[dict] = []
            for tc in tool_calls:
                raw_args = tc["function"]["arguments"]
                tool_args = _json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                parsed.append({
                    "tool_name": tc["function"]["name"],
                    "tool_args": tool_args,
                    "call_id": tc.get("id", ""),
                })
            return {"type": "tool_calls", "calls": parsed}

        content = message.get("content") or ""
        return {"type": "text", "content": content}

    async def _request_json(self, *, messages: list[dict[str, str]]) -> dict[str, Any] | None:
        """Execute a JSON-mode request, retrying once with each fallback model on failure."""
        if not self.available():
            return None

        candidate_models = [self.model, *self.fallback_models]
        for idx, model_name in enumerate(candidate_models):
            try:
                result = await self._request_json_single(messages=messages, model_name=model_name)
            except Exception as exc:
                logger.warning("LLM JSON call failed on model=%s (attempt %d): %s", model_name, idx + 1, exc)
                continue
            if result is not None:
                if idx > 0:
                    logger.info("LLM JSON fell back from %s to %s", self.model, model_name)
                return result
        return None

    async def _request_json_single(
        self,
        *,
        messages: list[dict[str, str]],
        model_name: str,
    ) -> dict[str, Any] | None:
        """Single-model JSON request. Raises on HTTP/transport error."""
        try:
            import httpx
        except Exception:
            return None

        payload = {
            "model": model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
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

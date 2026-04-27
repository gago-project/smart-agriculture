"""Redis-backed conversation message history.

Stores actual user/assistant message pairs (with tool calls and results)
so the LLM agent receives full conversation context each turn.
Previous slot-based storage is replaced; the LLM resolves multi-turn
context natively from message history.
"""
from __future__ import annotations

import json
from typing import Any


_MAX_MESSAGES = 20


class InMemoryRedisClient:
    """Async Redis-like in-memory client for tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        del ex
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


class SessionContextRepository:
    """Persist and load conversation message history for one chat session."""

    def __init__(self, redis_client=None, ttl_seconds: int = 7200) -> None:
        self.redis_client = redis_client or InMemoryRedisClient()
        self.ttl_seconds = ttl_seconds

    async def load_history(self, session_id: str) -> list[dict[str, Any]]:
        """Return all stored messages for a session in chronological order."""
        try:
            raw = await self.redis_client.get(self._key(session_id))
        except Exception:
            return []
        if not raw:
            return []
        return json.loads(raw).get("messages", [])

    async def save_message_turn(
        self,
        session_id: str,
        turn_id: int,
        *,
        user_message: str,
        assistant_message: str,
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> None:
        """Append one user+assistant turn using the standard OpenAI transcript format.

        The stored chain is:
          user → assistant(tool_calls) → tool(result) ... → assistant(final_text)
        """
        key = self._key(session_id)
        try:
            raw = await self.redis_client.get(key)
        except Exception:
            return
        messages: list[dict[str, Any]] = json.loads(raw).get("messages", []) if raw else []

        messages.append({"role": "user", "content": user_message})

        if tool_calls:
            # First assistant message: carries tool_calls, no final text yet
            messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
            # One tool result message per call
            for tc, tr in zip(tool_calls, tool_results):
                call_id = tc.get("id", "")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(tr, ensure_ascii=False),
                })

        # Final assistant message with the visible answer text
        messages.append({"role": "assistant", "content": assistant_message})

        messages = messages[-_MAX_MESSAGES:]
        try:
            await self.redis_client.set(
                key,
                json.dumps({"messages": messages}, ensure_ascii=False),
                ex=self.ttl_seconds,
            )
        except Exception:
            return

    async def clear_context(self, session_id: str) -> None:
        """Clear all message history for a session."""
        try:
            await self.redis_client.delete(self._key(session_id))
        except Exception:
            return

    def _key(self, session_id: str) -> str:
        return f"session_msg:{session_id}"

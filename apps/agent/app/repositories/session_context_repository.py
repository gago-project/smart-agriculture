"""Redis-backed conversation context repository.

The stored value is intentionally small: `latest_business_turns` keeps at most
five verified business contexts.  This supports safe follow-up questions while
avoiding persistence of full answers, SQL results, or sensitive debug payloads.
"""

from __future__ import annotations


import json
from datetime import datetime
from typing import Any


class InMemoryRedisClient:
    """Tiny async Redis-like client used when Redis is unavailable in tests."""

    def __init__(self) -> None:
        """Initialize an in-memory key/value store."""
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        """Return a value by key."""
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        """Store a value; TTL is ignored for the in-memory test client."""
        del ex
        self.store[key] = value

    async def delete(self, key: str) -> None:
        """Delete a key if present."""
        self.store.pop(key, None)


class SessionContextRepository:
    """Persist and load recent business contexts for one chat session."""

    def __init__(self, redis_client=None, ttl_seconds: int = 3600) -> None:
        """Accept a real Redis client or fall back to the in-memory client."""
        self.redis_client = redis_client or InMemoryRedisClient()
        self.ttl_seconds = ttl_seconds

    async def load_recent_context(self, session_id: str) -> list[dict[str, Any]]:
        """Load the most recent five business turns for a session."""
        try:
            raw = await self.redis_client.get(self._key(session_id))
        except Exception:
            return []
        if not raw:
            return []
        snapshot = json.loads(raw)
        return list(snapshot.get("latest_business_turns", []))[-5:]

    async def save_turn_context(self, session_id: str, turn_id: int, turn_context: dict[str, Any]) -> None:
        """Save one verified business turn with turn-id ordering protection."""
        key = self._key(session_id)
        try:
            raw = await self.redis_client.get(key)
        except Exception:
            return
        snapshot = json.loads(raw) if raw else {"latest_business_turns": []}
        turns = list(snapshot.get("latest_business_turns", []))
        latest_turn_id = max([item.get("turn_id", 0) for item in turns], default=0)
        if turn_id < latest_turn_id:
            # Late writes from an older turn must not overwrite newer context.
            return
        filtered = {
            "domain": turn_context.get("domain"),
            "region": turn_context.get("region") or {},
            "time_window": turn_context.get("time_window"),
            "entity_reference": turn_context.get("entity_reference"),
            "last_intent": turn_context.get("last_intent"),
            "turn_id": turn_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        turns = [item for item in turns if item.get("turn_id") != turn_id]
        turns.append(filtered)
        turns = sorted(turns, key=lambda item: item.get("turn_id", 0))[-5:]
        try:
            await self.redis_client.set(key, json.dumps({"latest_business_turns": turns}, ensure_ascii=False), ex=self.ttl_seconds)
        except Exception:
            return

    async def clear_context(self, session_id: str) -> None:
        """Clear all remembered context for a session."""
        try:
            await self.redis_client.delete(self._key(session_id))
        except Exception:
            return

    def _key(self, session_id: str) -> str:
        """Build the Redis key namespace for chat-session context."""
        return f"session_ctx:{session_id}"

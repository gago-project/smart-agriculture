"""Redis runtime wrapper for Agent conversation memory."""

from __future__ import annotations



class RedisRuntime:
    """Create an async Redis client from a URL when the dependency exists."""

    def __init__(self, url: str = "") -> None:
        """Store the Redis URL without opening a network connection yet."""
        self.url = url

    def available(self) -> bool:
        """Return whether Redis is configured."""
        return bool(self.url)

    def create_client(self):
        """Create a decode-responses Redis client, or `None` if unavailable."""
        try:
            from redis import asyncio as redis_asyncio
        except Exception:
            return None
        if not self.url:
            return None
        return redis_asyncio.from_url(self.url, decode_responses=True)

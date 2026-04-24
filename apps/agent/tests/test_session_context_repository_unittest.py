"""Unit tests for session context repository."""

from __future__ import annotations

import asyncio
import unittest

from app.repositories.session_context_repository import SessionContextRepository


class InMemoryRedis:
    """Test double for in memory redis."""
    def __init__(self) -> None:
        """Initialize the in memory redis."""
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        """Handle get on the in memory redis."""
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        """Handle set on the in memory redis."""
        self.store[key] = value

    async def delete(self, key: str) -> None:
        """Handle delete on the in memory redis."""
        self.store.pop(key, None)


class FailingRedis:
    """Test double for failing redis."""
    async def get(self, key: str) -> str | None:
        """Handle get on the failing redis."""
        del key
        raise ConnectionError("redis down")

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        """Handle set on the failing redis."""
        del key, value, ex
        raise ConnectionError("redis down")

    async def delete(self, key: str) -> None:
        """Handle delete on the failing redis."""
        del key
        raise ConnectionError("redis down")


class SessionContextRepositoryTest(unittest.TestCase):
    """Test cases for session context repository."""
    def test_save_turn_context_keeps_latest_five_turns_and_cas(self) -> None:
        """Verify save turn context keeps latest five turns and cas."""
        async def run_case() -> None:
            repository = SessionContextRepository(redis_client=InMemoryRedis())
            for turn_id in range(1, 8):
                await repository.save_turn_context(
                    session_id="session-1",
                    turn_id=turn_id,
                    turn_context={
                        "domain": "soil_moisture",
                        "region": {"county": f"区域-{turn_id}"},
                        "time_window": "last_7_days",
                        "entity_reference": {"county": f"区域-{turn_id}"},
                        "last_intent": "soil_recent_summary",
                    },
                )

            await repository.save_turn_context(
                session_id="session-1",
                turn_id=3,
                turn_context={
                    "domain": "soil_moisture",
                    "region": {"county": "旧区域"},
                    "time_window": "last_7_days",
                    "entity_reference": {"county": "旧区域"},
                    "last_intent": "soil_recent_summary",
                },
            )

            recent = await repository.load_recent_context("session-1")
            self.assertEqual(len(recent), 5)
            self.assertEqual([item["turn_id"] for item in recent], [3, 4, 5, 6, 7])
            self.assertEqual(recent[-1]["region"]["county"], "区域-7")
            self.assertNotEqual(recent[0]["region"]["county"], "旧区域")

        asyncio.run(run_case())

    def test_redis_connection_failure_should_fallback_to_empty_context(self) -> None:
        """Verify redis connection failure should fallback to empty context."""
        async def run_case() -> None:
            repository = SessionContextRepository(redis_client=FailingRedis())
            recent = await repository.load_recent_context("session-1")
            self.assertEqual(recent, [])
            await repository.save_turn_context(
                session_id="session-1",
                turn_id=1,
                turn_context={
                    "domain": "soil_moisture",
                    "region": {"county": "如东县"},
                    "time_window": "last_7_days",
                    "entity_reference": {"county": "如东县"},
                    "last_intent": "soil_recent_summary",
                },
            )

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()

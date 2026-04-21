from __future__ import annotations

import asyncio
import unittest

from app.repositories.session_context_repository import SessionContextRepository


class InMemoryRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


class SessionContextRepositoryTest(unittest.TestCase):
    def test_save_turn_context_keeps_latest_five_turns_and_cas(self) -> None:
        async def run_case() -> None:
            repository = SessionContextRepository(redis_client=InMemoryRedis())
            for turn_id in range(1, 8):
                await repository.save_turn_context(
                    session_id="session-1",
                    turn_id=turn_id,
                    turn_context={
                        "domain": "soil_moisture",
                        "region": {"county_name": f"区域-{turn_id}"},
                        "time_window": "last_7_days",
                        "entity_reference": {"county_name": f"区域-{turn_id}"},
                        "last_intent": "soil_recent_summary",
                    },
                )

            await repository.save_turn_context(
                session_id="session-1",
                turn_id=3,
                turn_context={
                    "domain": "soil_moisture",
                    "region": {"county_name": "旧区域"},
                    "time_window": "last_7_days",
                    "entity_reference": {"county_name": "旧区域"},
                    "last_intent": "soil_recent_summary",
                },
            )

            recent = await repository.load_recent_context("session-1")
            self.assertEqual(len(recent), 5)
            self.assertEqual([item["turn_id"] for item in recent], [3, 4, 5, 6, 7])
            self.assertEqual(recent[-1]["region"]["county_name"], "区域-7")
            self.assertNotEqual(recent[0]["region"]["county_name"], "旧区域")

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()

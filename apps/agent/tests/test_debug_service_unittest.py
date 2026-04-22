"""Unit tests for debug service."""

from __future__ import annotations

import asyncio
import unittest

from app.services.debug_service import DebugService


class DebugServiceTest(unittest.TestCase):
    """Test cases for debug service."""
    def test_save_and_list_trace_snapshots(self) -> None:
        """Verify save and list trace snapshots."""
        async def run_case() -> None:
            service = DebugService()
            await service.save_node_snapshot(
                trace_id="trace-1",
                request_id="req-1",
                session_id="session-1",
                turn_id=1,
                node_name="input_guard",
                status="success",
                started_at="2026-04-21T10:00:00",
                finished_at="2026-04-21T10:00:01",
                input_summary={"user_input": "最近墒情怎么样"},
                output_summary={"input_type": "business_direct"},
            )

            snapshots = service.list_trace_snapshots("trace-1")
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]["node_name"], "input_guard")
            self.assertEqual(snapshots[0]["status"], "success")

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()

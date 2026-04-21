from __future__ import annotations

import json
import unittest
from decimal import Decimal

from app.repositories.query_log_repository import QueryLogRepository


class FakeCursor:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.should_fail = should_fail

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        if self.should_fail:
            raise RuntimeError("write failed")
        self.executed.append((sql, params))


class FakeConnection:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.cursor_instance = FakeCursor(should_fail=should_fail)
        self.commit_called = False
        self.rollback_called = False
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_called = True

    def rollback(self) -> None:
        self.rollback_called = True

    def close(self) -> None:
        self.closed = True


class FakeRepository:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def _connect(self) -> FakeConnection:
        return self.connection


class QueryLogRepositoryTest(unittest.TestCase):
    def test_append_serializes_decimal_preview_and_commits(self) -> None:
        connection = FakeConnection()
        repository = QueryLogRepository(FakeRepository(connection))

        repository.append(
            {
                "query_id": "test-query",
                "session_id": "session-1",
                "turn_id": 1,
                "request_text": "最近墒情怎么样",
                "response_text": "当前样本整体墒情概况",
                "input_type": "business_direct",
                "intent": "soil_recent_summary",
                "answer_type": "soil_summary_answer",
                "final_status": "verified_end",
                "query_type": "recent_summary",
                "query_plan_json": {"sql_template": "SQL-01"},
                "time_range_json": {},
                "filters_json": {},
                "row_count": 1,
                "result_preview_json": [{"water20cm": Decimal("41.20")}],
                "status": "success",
            }
        )

        self.assertTrue(connection.commit_called)
        self.assertFalse(connection.rollback_called)
        self.assertEqual(len(connection.cursor_instance.executed), 1)

        _, params = connection.cursor_instance.executed[0]
        self.assertEqual(params[3], "最近墒情怎么样")
        self.assertEqual(params[4], "当前样本整体墒情概况")
        result_preview_json = json.loads(params[19])
        self.assertEqual(result_preview_json, [{"water20cm": 41.2}])

    def test_append_raises_and_does_not_keep_memory_log_when_mysql_write_fails(self) -> None:
        connection = FakeConnection(should_fail=True)
        repository = QueryLogRepository(FakeRepository(connection))

        with self.assertRaises(RuntimeError):
            repository.append(
                {
                    "query_id": "failed-query",
                    "session_id": "session-1",
                    "turn_id": 1,
                    "query_type": "recent_summary",
                    "query_plan_json": {},
                    "time_range_json": {},
                    "filters_json": {},
                    "row_count": 0,
                    "status": "failed",
                }
            )

        self.assertTrue(connection.rollback_called)
        self.assertTrue(connection.closed)
        self.assertEqual(repository.logs, [])


if __name__ == "__main__":
    unittest.main()

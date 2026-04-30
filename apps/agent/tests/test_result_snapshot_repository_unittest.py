"""Unit tests for snapshot persistence behavior."""

from __future__ import annotations

import json
import unittest
from decimal import Decimal

from app.repositories.result_snapshot_repository import ResultSnapshotRepository


class RecordingCursor:
    """Capture executed SQL statements for snapshot persistence tests."""

    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))
        if self.connection.fail_on_execute_index is not None:
            self.connection.execute_count += 1
            if self.connection.execute_count == self.connection.fail_on_execute_index:
                raise RuntimeError("insert failed")

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class RecordingConnection:
    """Test double for one snapshot transaction."""

    def __init__(self, *, fail_on_execute_index: int | None = None, rollback_raises: bool = False) -> None:
        self.executed: list[tuple[str, object]] = []
        self.execute_count = 0
        self.fail_on_execute_index = fail_on_execute_index
        self.rollback_raises = rollback_raises
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True
        if self.rollback_raises:
            raise RuntimeError("rollback failed")

    def close(self) -> None:
        self.closed = True


class SnapshotRepositoryBackedByConnection:
    """Tiny repository stub that exposes `_connect`."""

    def __init__(self, connection: RecordingConnection) -> None:
        self.connection = connection

    def _connect(self) -> RecordingConnection:
        return self.connection


class ResultSnapshotRepositoryTest(unittest.TestCase):
    """Verify snapshot inserts stay chunked and preserve root-cause errors."""

    def test_create_snapshot_inserts_items_in_batches(self) -> None:
        connection = RecordingConnection()
        repository = ResultSnapshotRepository(
            repository=SnapshotRepositoryBackedByConnection(connection),
            insert_batch_size=100,
        )
        rows = [{"sn": f"SNS{i:08d}", "city": "南通市", "county": "如东县"} for i in range(205)]

        snapshot = repository.create_snapshot(
            session_id="session-1",
            source_turn_id=1,
            source_block_id="block_summary_1",
            snapshot_kind="focus_devices",
            query_spec={"capability": "summary"},
            rule_version="rule-v1",
            rows=rows,
        )

        item_inserts = [sql for sql, _params in connection.executed if "INSERT INTO agent_result_snapshot_item" in sql]
        self.assertEqual(snapshot["total_count"], 205)
        self.assertEqual(len(item_inserts), 3)
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

    def test_create_snapshot_serializes_decimal_fields_for_json_columns(self) -> None:
        connection = RecordingConnection()
        repository = ResultSnapshotRepository(repository=SnapshotRepositoryBackedByConnection(connection))

        repository.create_snapshot(
            session_id="session-1",
            source_turn_id=1,
            source_block_id="block_summary_1",
            snapshot_kind="focus_devices",
            query_spec={"capability": "summary", "threshold": Decimal("41.20")},
            rule_version="rule-v1",
            rows=[{"sn": "SNS00000001", "city": "南通市", "county": "如东县", "water20cm": Decimal("41.20")}],
        )

        snapshot_insert_params = connection.executed[0][1]
        item_insert_params = connection.executed[1][1]
        self.assertEqual(json.loads(snapshot_insert_params[5])["threshold"], 41.2)
        self.assertEqual(json.loads(item_insert_params[10])["water20cm"], 41.2)
        self.assertTrue(connection.committed)

    def test_create_snapshot_keeps_original_error_when_rollback_also_fails(self) -> None:
        connection = RecordingConnection(fail_on_execute_index=2, rollback_raises=True)
        repository = ResultSnapshotRepository(repository=SnapshotRepositoryBackedByConnection(connection))

        with self.assertRaisesRegex(RuntimeError, "insert failed"):
            repository.create_snapshot(
                session_id="session-1",
                source_turn_id=1,
                source_block_id="block_summary_1",
                snapshot_kind="focus_devices",
                query_spec={"capability": "summary"},
                rule_version="rule-v1",
                rows=[{"sn": "SNS00000001"}],
            )

        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)

    def test_get_snapshot_escapes_date_format_percent_for_pyformat(self) -> None:
        connection = SnapshotLookupConnection()
        repository = ResultSnapshotRepository(repository=SnapshotRepositoryBackedByConnection(connection))

        snapshot = repository.get_snapshot("snap-1")

        self.assertEqual(snapshot["snapshot_id"], "snap-1")
        self.assertEqual(snapshot["items"][0]["sn"], "SNS0001")


class SnapshotLookupCursor:
    """Cursor double that fails if DATE_FORMAT markers are not escaped."""

    def __init__(self) -> None:
        self.execute_calls = 0

    def __enter__(self) -> "SnapshotLookupCursor":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def execute(self, sql, params=None):
        self.execute_calls += 1
        self.rendered = sql % params

    def fetchone(self):
        if self.execute_calls != 1:
            return None
        return {
            "snapshot_id": "snap-1",
            "session_id": "session-1",
            "source_turn_id": 1,
            "source_block_id": "block_summary_1",
            "snapshot_kind": "focus_devices",
            "query_spec_json": "{}",
            "query_spec_hash": "hash-1",
            "rule_version": "rule-v1",
            "total_count": 1,
            "expires_at": "2026-05-01 00:00:00",
            "created_at": "2026-04-30 00:00:00",
        }

    def fetchall(self):
        if self.execute_calls != 2:
            return []
        return [
            {
                "row_index": 0,
                "entity_key": "device:SNS0001",
                "city": "南通市",
                "county": "如东县",
                "sn": "SNS0001",
                "soil_status": "heavy_drought",
                "warning_level": "heavy_drought",
                "risk_score": 88.2,
                "latest_create_time": "2026-04-30 00:00:00",
                "payload_json": "{}",
            }
        ]


class SnapshotLookupConnection:
    """Connection wrapper for snapshot lookup tests."""

    def __init__(self) -> None:
        self.closed = False

    def cursor(self) -> SnapshotLookupCursor:
        return SnapshotLookupCursor()

    def close(self) -> None:
        self.closed = True

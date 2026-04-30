"""Snapshot persistence for deterministic data-answer follow-up flows."""

from __future__ import annotations


import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4


_DERIVED_RESULT_KEYS = {"soil_status", "warning_level", "risk_score", "display_label", "rule_version"}


def _parse_json_value(value: Any) -> Any:
    """Normalize a DB JSON cell into plain Python data."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _json_default(value: Any) -> Any:
    """Convert DB-native scalar values into JSON-safe primitives."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_dumps(value: Any, *, sort_keys: bool = False) -> str:
    """Serialize snapshot JSON columns with Decimal/date support."""
    return json.dumps(value, ensure_ascii=False, default=_json_default, sort_keys=sort_keys)


@dataclass
class ResultSnapshotRepository:
    """Persist and read result snapshots in MySQL, with in-memory fallback for tests."""

    repository: Any
    ttl_days: int = 30
    insert_batch_size: int = 100

    def __post_init__(self) -> None:
        self._memory_snapshots: dict[str, dict[str, Any]] = {}

    def _open_connection(self):
        """Return a short-lived DB connection when the backing repository supports it."""
        connector = getattr(self.repository, "_connect", None)
        if not callable(connector):
            return None
        connection = connector()
        return connection

    @staticmethod
    def _snapshot_id() -> str:
        return f"snap_{uuid4().hex[:24]}"

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        payload_json = {key: value for key, value in row.items() if key not in _DERIVED_RESULT_KEYS}
        return {
            "entity_key": str(
                row.get("entity_key")
                or row.get("sn")
                or row.get("county")
                or row.get("city")
                or row.get("id")
                or ""
            ),
            "city": row.get("city"),
            "county": row.get("county"),
            "sn": row.get("sn"),
            "latest_create_time": row.get("latest_create_time") or row.get("create_time"),
            "payload_json": payload_json,
        }

    def _insert_snapshot_items(self, cursor: Any, snapshot_id: str, normalized_rows: list[dict[str, Any]]) -> None:
        """Insert snapshot items in bounded batches to avoid oversized single statements."""
        batch_size = max(1, int(self.insert_batch_size or 100))
        for start in range(0, len(normalized_rows), batch_size):
            batch = normalized_rows[start : start + batch_size]
            value_placeholders = ", ".join(["(%s, %s, %s, %s, %s, %s, %s, %s)"] * len(batch))
            values: list[Any] = []
            for offset, row in enumerate(batch, start=start):
                values.extend(
                    [
                        snapshot_id,
                        offset,
                        row["entity_key"],
                        row["city"],
                        row["county"],
                        row["sn"],
                        row["latest_create_time"],
                        _json_dumps(row["payload_json"]),
                    ]
                )
            cursor.execute(
                f"""
                INSERT INTO agent_result_snapshot_item (
                  snapshot_id,
                  row_index,
                  entity_key,
                  city,
                  county,
                  sn,
                  latest_create_time,
                  payload_json
                ) VALUES {value_placeholders}
                """,
                values,
            )

    def create_snapshot(
        self,
        *,
        session_id: str,
        source_turn_id: int,
        source_block_id: str,
        snapshot_kind: str,
        query_spec: dict[str, Any],
        rule_version: str | None,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Persist one snapshot and its items, or store it in memory for unit tests."""
        snapshot_id = self._snapshot_id()
        normalized_rows = [self._normalize_row(row) for row in rows]
        expires_at = (datetime.now() + timedelta(days=self.ttl_days)).strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "snapshot_id": snapshot_id,
            "session_id": session_id,
            "source_turn_id": source_turn_id,
            "source_block_id": source_block_id,
            "snapshot_kind": snapshot_kind,
            "query_spec_json": query_spec,
            "query_spec_hash": hashlib.sha1(
                _json_dumps(query_spec, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "rule_version": rule_version,
            "total_count": len(normalized_rows),
            "expires_at": expires_at,
            "items": normalized_rows,
        }

        connection = self._open_connection()
        if connection is None:
            self._memory_snapshots[snapshot_id] = payload
            return payload

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_result_snapshot (
                      snapshot_id,
                      session_id,
                      source_turn_id,
                      source_block_id,
                      snapshot_kind,
                      query_spec_json,
                      query_spec_hash,
                      rule_version,
                      total_count,
                      expires_at,
                      created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        snapshot_id,
                        session_id,
                        source_turn_id,
                        source_block_id,
                        snapshot_kind,
                        _json_dumps(query_spec),
                        payload["query_spec_hash"],
                        rule_version,
                        len(normalized_rows),
                        expires_at,
                    ),
                )
                if normalized_rows:
                    self._insert_snapshot_items(cursor, snapshot_id, normalized_rows)
            connection.commit()
            return payload
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
            raise
        finally:
            connection.close()

    async def create_snapshot_async(self, **kwargs) -> dict[str, Any]:
        """Async wrapper for snapshot creation."""
        return await asyncio.to_thread(self.create_snapshot, **kwargs)

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        """Return snapshot metadata and all items."""
        if snapshot_id in self._memory_snapshots:
            return self._memory_snapshots[snapshot_id]

        connection = self._open_connection()
        if connection is None:
            return None

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT snapshot_id, session_id, source_turn_id, source_block_id, snapshot_kind,
                           query_spec_json, query_spec_hash, rule_version, total_count,
                           DATE_FORMAT(expires_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS expires_at,
                           DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS created_at
                    FROM agent_result_snapshot
                    WHERE snapshot_id = %s
                    LIMIT 1
                    """,
                    (snapshot_id,),
                )
                snapshot_row = cursor.fetchone()
                if not snapshot_row:
                    return None
                cursor.execute(
                    """
                    SELECT row_index, entity_key, city, county, sn,
                           DATE_FORMAT(latest_create_time, '%%Y-%%m-%%d %%H:%%i:%%s') AS latest_create_time,
                           payload_json
                    FROM agent_result_snapshot_item
                    WHERE snapshot_id = %s
                    ORDER BY row_index ASC
                    """,
                    (snapshot_id,),
                )
                items = []
                for row in cursor.fetchall():
                    payload = _parse_json_value(row.get("payload_json")) or {}
                    items.append(
                        {
                            "row_index": row.get("row_index"),
                            "entity_key": row.get("entity_key"),
                            "city": row.get("city"),
                            "county": row.get("county"),
                            "sn": row.get("sn"),
                            "latest_create_time": row.get("latest_create_time"),
                            "payload_json": payload,
                        }
                    )
                return {
                    **snapshot_row,
                    "query_spec_json": _parse_json_value(snapshot_row.get("query_spec_json")) or {},
                    "items": items,
                }
        finally:
            connection.close()

    async def get_snapshot_async(self, snapshot_id: str) -> dict[str, Any] | None:
        """Async wrapper for snapshot lookup."""
        return await asyncio.to_thread(self.get_snapshot, snapshot_id)

from __future__ import annotations

"""Repository for persisting Agent query audit logs.

Every executed data query should produce an `agent_query_log` record containing
the query plan, SQL template fingerprint, filters, row count, and result
preview.  The in-memory `logs` list is kept for tests; MySQL remains the real
runtime persistence target.
"""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.repositories.soil_repository import DatabaseQueryError, SoilRepository


class QueryLogRepository:
    """Write query-log entries to memory and MySQL."""

    def __init__(self, soil_repository: SoilRepository | None = None) -> None:
        """Use the same soil repository configuration as query execution."""
        self.soil_repository = soil_repository or SoilRepository.from_env()
        self.logs: list[dict[str, Any]] = []

    def append(self, payload: dict[str, Any]) -> None:
        """Synchronous insert helper used by legacy tests."""
        normalized = self._normalize(payload)
        self._write_to_mysql(normalized)
        self.logs.append(dict(normalized))

    async def insert_query_log(self, payload: dict[str, Any]) -> None:
        """Insert one query-log payload asynchronously."""
        await self.insert_many([payload])

    async def insert_many(self, entries: list[dict[str, Any]]) -> None:
        """Normalize and persist multiple query-log entries."""
        for entry in entries:
            normalized = self._normalize(entry)
            await self._write_to_storage_async(normalized)
            self.logs.append(dict(normalized))

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Fill defaults and coerce types before writing to storage."""
        normalized = {
            "query_id": payload.get("query_id"),
            "session_id": payload.get("session_id"),
            "turn_id": int(payload.get("turn_id") or 0),
            "request_text": payload.get("request_text"),
            "response_text": payload.get("response_text"),
            "input_type": payload.get("input_type"),
            "intent": payload.get("intent"),
            "answer_type": payload.get("answer_type"),
            "final_status": payload.get("final_status"),
            "query_type": payload.get("query_type"),
            "query_plan_json": dict(payload.get("query_plan_json") or {}),
            "sql_fingerprint": payload.get("sql_fingerprint"),
            "time_range_json": dict(payload.get("time_range_json") or {}),
            "filters_json": dict(payload.get("filters_json") or {}),
            "group_by_json": payload.get("group_by_json"),
            "metrics_json": payload.get("metrics_json"),
            "order_by_json": payload.get("order_by_json"),
            "limit_size": payload.get("limit_size"),
            "row_count": int(payload.get("row_count") or 0),
            "result_preview_json": payload.get("result_preview_json"),
            "source_files_json": payload.get("source_files_json"),
            "status": payload.get("status") or "success",
            "error_message": payload.get("error_message"),
            "created_at": payload.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return normalized

    def _json_dumps(self, value: Any) -> str:
        """Serialize JSON columns with support for Decimal/date values."""
        return json.dumps(value, ensure_ascii=False, default=self._json_default)

    @staticmethod
    def _json_default(value: Any) -> Any:
        """Convert database-native values into JSON-compatible primitives."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat(sep=" ")
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def _write_to_mysql(self, payload: dict[str, Any]) -> None:
        """Persist one normalized query-log row through PyMySQL."""
        connection = self.soil_repository._connect()
        if not connection:
            return
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_query_log (
                      query_id, session_id, turn_id, request_text, response_text,
                      input_type, intent, answer_type, final_status,
                      query_type, query_plan_json,
                      sql_fingerprint, time_range_json, filters_json, group_by_json,
                      metrics_json, order_by_json, limit_size, row_count,
                      result_preview_json, source_files_json, status, error_message, created_at
                    ) VALUES (
                      %s, %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                      request_text = VALUES(request_text),
                      response_text = VALUES(response_text),
                      input_type = VALUES(input_type),
                      intent = VALUES(intent),
                      answer_type = VALUES(answer_type),
                      final_status = VALUES(final_status),
                      query_type = VALUES(query_type),
                      query_plan_json = VALUES(query_plan_json),
                      sql_fingerprint = VALUES(sql_fingerprint),
                      time_range_json = VALUES(time_range_json),
                      filters_json = VALUES(filters_json),
                      group_by_json = VALUES(group_by_json),
                      metrics_json = VALUES(metrics_json),
                      order_by_json = VALUES(order_by_json),
                      limit_size = VALUES(limit_size),
                      row_count = VALUES(row_count),
                      result_preview_json = VALUES(result_preview_json),
                      source_files_json = VALUES(source_files_json),
                      status = VALUES(status),
                      error_message = VALUES(error_message),
                      created_at = VALUES(created_at)
                    """,
                    (
                        payload["query_id"],
                        payload["session_id"],
                        payload["turn_id"],
                        payload["request_text"],
                        payload["response_text"],
                        payload["input_type"],
                        payload["intent"],
                        payload["answer_type"],
                        payload["final_status"],
                        payload["query_type"],
                        self._json_dumps(payload["query_plan_json"]),
                        payload["sql_fingerprint"],
                        self._json_dumps(payload["time_range_json"]),
                        self._json_dumps(payload["filters_json"]),
                        self._json_dumps(payload["group_by_json"]) if payload.get("group_by_json") is not None else None,
                        self._json_dumps(payload["metrics_json"]) if payload.get("metrics_json") is not None else None,
                        self._json_dumps(payload["order_by_json"]) if payload.get("order_by_json") is not None else None,
                        payload["limit_size"],
                        payload["row_count"],
                        self._json_dumps(payload["result_preview_json"]) if payload.get("result_preview_json") is not None else None,
                        self._json_dumps(payload["source_files_json"]) if payload.get("source_files_json") is not None else None,
                        payload["status"],
                        payload["error_message"],
                        payload["created_at"],
                    ),
                )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            raise DatabaseQueryError(f"agent_query_log 写入失败，已禁止内存日志兜底：{exc}") from exc
        finally:
            connection.close()

    async def _write_to_storage_async(self, payload: dict[str, Any]) -> None:
        """Prefer async SQLAlchemy writes; fall back to threaded PyMySQL."""
        async_database = getattr(self.soil_repository, "async_database", None)
        engine = async_database.create_engine() if async_database else None
        if engine is not None:
            try:
                from sqlalchemy import text
            except Exception:
                await asyncio.to_thread(self._write_to_mysql, payload)
                return
            try:
                async with engine.begin() as connection:
                    await connection.execute(
                        text(
                            """
                            INSERT INTO agent_query_log (
                              query_id, session_id, turn_id, request_text, response_text,
                              input_type, intent, answer_type, final_status,
                              query_type, query_plan_json,
                              sql_fingerprint, time_range_json, filters_json, group_by_json,
                              metrics_json, order_by_json, limit_size, row_count,
                              result_preview_json, source_files_json, status, error_message, created_at
                            ) VALUES (
                              :query_id, :session_id, :turn_id, :request_text, :response_text,
                              :input_type, :intent, :answer_type, :final_status,
                              :query_type, :query_plan_json,
                              :sql_fingerprint, :time_range_json, :filters_json, :group_by_json,
                              :metrics_json, :order_by_json, :limit_size, :row_count,
                              :result_preview_json, :source_files_json, :status, :error_message, :created_at
                            )
                            """
                        ),
                        {
                            "query_id": payload["query_id"],
                            "session_id": payload["session_id"],
                            "turn_id": payload["turn_id"],
                            "request_text": payload["request_text"],
                            "response_text": payload["response_text"],
                            "input_type": payload["input_type"],
                            "intent": payload["intent"],
                            "answer_type": payload["answer_type"],
                            "final_status": payload["final_status"],
                            "query_type": payload["query_type"],
                            "query_plan_json": self._json_dumps(payload["query_plan_json"]),
                            "sql_fingerprint": payload["sql_fingerprint"],
                            "time_range_json": self._json_dumps(payload["time_range_json"]),
                            "filters_json": self._json_dumps(payload["filters_json"]),
                            "group_by_json": self._json_dumps(payload["group_by_json"]) if payload.get("group_by_json") is not None else None,
                            "metrics_json": self._json_dumps(payload["metrics_json"]) if payload.get("metrics_json") is not None else None,
                            "order_by_json": self._json_dumps(payload["order_by_json"]) if payload.get("order_by_json") is not None else None,
                            "limit_size": payload["limit_size"],
                            "row_count": payload["row_count"],
                            "result_preview_json": self._json_dumps(payload["result_preview_json"]) if payload.get("result_preview_json") is not None else None,
                            "source_files_json": self._json_dumps(payload["source_files_json"]) if payload.get("source_files_json") is not None else None,
                            "status": payload["status"],
                            "error_message": payload["error_message"],
                            "created_at": payload["created_at"],
                        },
                    )
                return
            except Exception:
                pass
            finally:
                await engine.dispose()
        await asyncio.to_thread(self._write_to_mysql, payload)

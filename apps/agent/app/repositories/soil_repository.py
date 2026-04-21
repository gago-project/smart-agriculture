from __future__ import annotations

"""MySQL-backed repository for soil-moisture facts.

This repository is the data authority for the Python Agent.  It intentionally
does not contain seed-data fallback behavior: missing credentials, connection
failures, and SQL errors are surfaced as explicit exceptions so API callers see
real operational failures instead of fabricated agriculture facts.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from app.db.mysql import MySQLDatabase


DEFAULT_WARNING_TEMPLATE_TEXT = "{year} 年 {month} 月 {day} 日 {hour} 时 {city_name} {county_name} SN 编号 {device_sn} 土壤墒情仪监测到相对含水量 {water20cm}%，预警等级 {warning_level}，请大田/设施大棚/林果相关主体关注！"


class DatabaseUnavailableError(RuntimeError):
    """Raised when MySQL cannot be configured or connected."""

    pass


class DatabaseQueryError(RuntimeError):
    """Raised when a configured MySQL query fails."""

    pass


def _safe_float(value: Any) -> float | None:
    """Convert MySQL decimal/string values to floats for rule calculations."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evaluate_record_status(record: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the built-in fallback warning status for one record."""
    water20 = _safe_float(record.get("water20cm")) or 0.0
    t20 = _safe_float(record.get("t20cm")) or 0.0
    if water20 == 0 and t20 == 0:
        return {
            "soil_status": "device_fault",
            "warning_level": "device_fault",
            "display_label": "设备故障",
            "soil_anomaly_score": 100.0,
        }
    if water20 < 50:
        return {
            "soil_status": "heavy_drought",
            "warning_level": "heavy_drought",
            "display_label": "重旱",
            "soil_anomaly_score": round(90 + (50 - water20), 2),
        }
    if water20 >= 150:
        return {
            "soil_status": "waterlogging",
            "warning_level": "waterlogging",
            "display_label": "涝渍",
            "soil_anomaly_score": round(80 + (water20 - 150), 2),
        }
    return {
        "soil_status": "not_triggered",
        "warning_level": "none",
        "display_label": "未达到预警条件",
        "soil_anomaly_score": round(max(0.0, 70 - abs(water20 - 85) / 2), 2),
    }


@dataclass
class SoilRepository:
    """Repository that exposes read-only soil fact queries for the Agent."""

    mysql_host: str | None = None
    mysql_port: int | None = None
    mysql_database: str | None = None
    mysql_user: str | None = None
    mysql_password: str | None = None
    async_database: MySQLDatabase | None = None

    @classmethod
    def from_env(cls) -> "SoilRepository":
        """Build repository configuration from process environment variables."""
        mysql_host = os.getenv("MYSQL_HOST")
        mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
        mysql_database = os.getenv("MYSQL_DATABASE")
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD")
        async_database = None
        if all([mysql_host, mysql_database, mysql_user, mysql_password]):
            encoded_password = quote_plus(mysql_password or "")
            async_database = MySQLDatabase(
                f"mysql+asyncmy://{mysql_user}:{encoded_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4"
            )
        return cls(
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_database=mysql_database,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            async_database=async_database,
        )

    def _connect(self):
        """Open a short-lived PyMySQL connection or raise an explicit error."""
        if not all([self.mysql_host, self.mysql_database, self.mysql_user, self.mysql_password]):
            raise DatabaseUnavailableError("MySQL 配置不完整，已禁止使用种子数据兜底。")
        try:
            import pymysql
            return pymysql.connect(
                host=self.mysql_host,
                port=self.mysql_port or 3306,
                user=self.mysql_user,
                password=self.mysql_password,
                database=self.mysql_database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=2,
                read_timeout=3,
                write_timeout=3,
            )
        except Exception as exc:
            raise DatabaseUnavailableError(f"MySQL 连接失败，已禁止使用种子数据兜底：{exc}") from exc

    def latest_records(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return latest records synchronously for legacy callers."""
        return self.filter_records(limit=limit)

    async def latest_records_async(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return latest records through the async query path."""
        return await self.filter_records_async(limit=limit)

    def filter_records(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        device_sn: str | None = None,
        batch_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Filter soil facts with optional region/device/batch/time predicates."""
        connection = self._connect()
        try:
            clauses = []
            params: list[Any] = []
            if city_name:
                clauses.append("city_name = %s")
                params.append(city_name)
            if county_name:
                clauses.append("county_name = %s")
                params.append(county_name)
            if town_name:
                clauses.append("town_name = %s")
                params.append(town_name)
            if device_sn:
                clauses.append("device_sn = %s")
                params.append(device_sn)
            if batch_id:
                clauses.append("batch_id = %s")
                params.append(batch_id)
            if start_time:
                clauses.append("sample_time >= %s")
                params.append(start_time)
            if end_time:
                clauses.append("sample_time <= %s")
                params.append(end_time)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            limit_sql = f"LIMIT {int(limit)}" if limit else ""
            with connection.cursor() as cursor:
                # The SQL is built from a fixed column list and fixed optional
                # predicates.  User values always enter through parameters.
                cursor.execute(
                    f"""
                    SELECT batch_id, device_sn, device_name, city_name, county_name, town_name,
                           DATE_FORMAT(sample_time, '%%Y-%%m-%%d %%H:%%i:%%s') AS sample_time,
                           DATE_FORMAT(create_time, '%%Y-%%m-%%d %%H:%%i:%%s') AS create_time,
                           water20cm, water40cm, water60cm, water80cm, t20cm, t40cm, t60cm, t80cm,
                           soil_anomaly_type, soil_anomaly_score, source_file, source_sheet, source_row
                    FROM fact_soil_moisture
                    {where_sql}
                    ORDER BY sample_time DESC
                    {limit_sql}
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
                enriched = [{**row, **_evaluate_record_status(row)} for row in rows]
                return enriched
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询失败，已禁止使用种子数据兜底：{exc}") from exc
        finally:
            connection.close()

    async def filter_records_async(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        device_sn: str | None = None,
        batch_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Async wrapper that prefers SQLAlchemy async engine and falls back to a thread."""
        async_rows = await self._filter_records_with_async_engine(
            city_name=city_name,
            county_name=county_name,
            town_name=town_name,
            device_sn=device_sn,
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        if async_rows is not None:
            return async_rows
        return await asyncio.to_thread(
            self.filter_records,
            city_name=city_name,
            county_name=county_name,
            town_name=town_name,
            device_sn=device_sn,
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def _filter_records_with_async_engine(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        device_sn: str | None = None,
        batch_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | None:
        """Execute the same fixed query through SQLAlchemy async engine if available."""
        if not self.async_database:
            return None
        engine = self.async_database.create_engine()
        if engine is None:
            return None
        try:
            try:
                from sqlalchemy import text
            except Exception:
                return None
            clauses = []
            params: dict[str, Any] = {}
            if city_name:
                clauses.append("city_name = :city_name")
                params["city_name"] = city_name
            if county_name:
                clauses.append("county_name = :county_name")
                params["county_name"] = county_name
            if town_name:
                clauses.append("town_name = :town_name")
                params["town_name"] = town_name
            if device_sn:
                clauses.append("device_sn = :device_sn")
                params["device_sn"] = device_sn
            if batch_id:
                clauses.append("batch_id = :batch_id")
                params["batch_id"] = batch_id
            if start_time:
                clauses.append("sample_time >= :start_time")
                params["start_time"] = start_time
            if end_time:
                clauses.append("sample_time <= :end_time")
                params["end_time"] = end_time
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            limit_sql = f"LIMIT {int(limit)}" if limit else ""
            sql = text(
                f"""
                SELECT batch_id, device_sn, device_name, city_name, county_name, town_name,
                       DATE_FORMAT(sample_time, '%Y-%m-%d %H:%i:%s') AS sample_time,
                       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
                       water20cm, water40cm, water60cm, water80cm, t20cm, t40cm, t60cm, t80cm,
                       soil_anomaly_type, soil_anomaly_score, source_file, source_sheet, source_row
                FROM fact_soil_moisture
                {where_sql}
                ORDER BY sample_time DESC
                {limit_sql}
                """
            )
            async with engine.connect() as connection:
                result = await connection.execute(sql, params)
                rows = [dict(row._mapping) for row in result]
                return [{**row, **_evaluate_record_status(row)} for row in rows]
        except Exception:
            return None
        finally:
            await engine.dispose()

    def latest_record_by_device(self, device_sn: str) -> dict[str, Any] | None:
        """Return the newest record for one device SN."""
        records = self.filter_records(device_sn=device_sn, limit=1)
        return records[0] if records else None

    def latest_business_time(self) -> str:
        """Return latest `sample_time` from facts, not the current wall clock."""
        records = self.filter_records(limit=1)
        return str(records[0].get("sample_time")) if records else "暂无"

    async def latest_business_time_async(self) -> str:
        """Async latest-business-time lookup used by time resolution."""
        records = await self.filter_records_async(limit=1)
        return str(records[0].get("sample_time")) if records else "暂无"

    def latest_batch_id(self) -> str | None:
        """Return newest imported batch id from `etl_import_batch`."""
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT batch_id
                    FROM etl_import_batch
                    ORDER BY COALESCE(finished_at, started_at) DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if row and row.get("batch_id"):
                    return str(row["batch_id"])
                return None
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询最新批次失败，已禁止使用种子数据兜底：{exc}") from exc
        finally:
            connection.close()

    async def latest_batch_id_async(self) -> str | None:
        """Async wrapper for latest batch id lookup."""
        return await asyncio.to_thread(self.latest_batch_id)

    def known_region_names(self) -> set[str]:
        """Return known city/county/town names observed in the fact table."""
        names = set()
        for record in self.filter_records():
            if record.get("city_name"):
                names.add(record["city_name"])
            if record.get("county_name"):
                names.add(record["county_name"])
            if record.get("town_name"):
                names.add(record["town_name"])
        return names

    async def known_region_names_async(self) -> set[str]:
        """Async variant of known-region discovery."""
        records = await self.filter_records_async()
        names = set()
        for record in records:
            if record.get("city_name"):
                names.add(record["city_name"])
            if record.get("county_name"):
                names.add(record["county_name"])
            if record.get("town_name"):
                names.add(record["town_name"])
        return names

    def region_exists(self, region_name: str) -> bool:
        """Return whether a region name appears in known fact records."""
        return region_name in self.known_region_names()

    async def region_exists_async(self, region_name: str) -> bool:
        """Async region existence check."""
        return region_name in await self.known_region_names_async()

    def device_exists(self, device_sn: str) -> bool:
        """Return whether a device SN appears in known fact records."""
        return any(record.get("device_sn") == device_sn for record in self.filter_records())

    async def device_exists_async(self, device_sn: str) -> bool:
        """Async device existence check."""
        return any(record.get("device_sn") == device_sn for record in await self.filter_records_async())

    def region_record_count(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        batch_id: str | None = None,
    ) -> int:
        """Count records matching one region/batch combination."""
        return len(
            self.filter_records(
                city_name=city_name,
                county_name=county_name,
                town_name=town_name,
                batch_id=batch_id,
            )
        )

    def device_record_count(self, device_sn: str, *, batch_id: str | None = None) -> int:
        """Count records for one device, optionally constrained to a batch."""
        return len(self.filter_records(device_sn=device_sn, batch_id=batch_id))

    async def region_record_count_async(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        batch_id: str | None = None,
    ) -> int:
        """Async region record count used by SQL-07 fallback checks."""
        return len(
            await self.filter_records_async(
                city_name=city_name,
                county_name=county_name,
                town_name=town_name,
                batch_id=batch_id,
            )
        )

    async def device_record_count_async(self, device_sn: str, *, batch_id: str | None = None) -> int:
        """Async device record count used by SQL-07 fallback checks."""
        return len(await self.filter_records_async(device_sn=device_sn, batch_id=batch_id))

    def period_record_summary(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        device_sn: str | None = None,
        batch_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Return count and latest sample time for a fallback time-period check."""
        records = self.filter_records(
            city_name=city_name,
            county_name=county_name,
            town_name=town_name,
            device_sn=device_sn,
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
        )
        latest_sample_time = max((str(item.get("sample_time") or "") for item in records), default=None)
        return {
            "period_record_count": len(records),
            "latest_sample_time": latest_sample_time or self.latest_business_time(),
        }

    async def period_record_summary_async(
        self,
        *,
        city_name: str | None = None,
        county_name: str | None = None,
        town_name: str | None = None,
        device_sn: str | None = None,
        batch_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Async period summary used by fallback existence diagnostics."""
        records = await self.filter_records_async(
            city_name=city_name,
            county_name=county_name,
            town_name=town_name,
            device_sn=device_sn,
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
        )
        latest_sample_time = max((str(item.get("sample_time") or "") for item in records), default=None)
        return {
            "period_record_count": len(records),
            "latest_sample_time": latest_sample_time or await self.latest_business_time_async(),
        }

    def warning_template_text(self) -> str:
        """Return the default warning template text for rendering services."""
        return DEFAULT_WARNING_TEMPLATE_TEXT

    def evaluate_status(self, record: dict[str, Any]) -> dict[str, Any]:
        """Expose built-in record status evaluation for dashboard summaries."""
        return _evaluate_record_status(record)

"""MySQL-backed repository for soil-moisture facts."""

from __future__ import annotations


import asyncio
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

from app.db.mysql import MySQLDatabase


DEFAULT_WARNING_TEMPLATE_TEXT = "{year} 年 {month} 月 {day} 日 {hour} 时 {city} {county} SN 编号 {sn} 土壤墒情仪监测到相对含水量 {water20cm}%，预警等级 {warning_level}，请大田/设施大棚/林果相关主体关注！"


class DatabaseUnavailableError(RuntimeError):
    """Raised when MySQL cannot be configured or connected."""


class DatabaseQueryError(RuntimeError):
    """Raised when a configured MySQL query fails."""


def _safe_float(value: Any) -> float | None:
    """Convert MySQL decimal/string values to floats for rule calculations."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evaluate_record_status(
    record: dict[str, Any],
    rule_profile: "Any | None" = None,
) -> dict[str, Any]:
    """Evaluate warning status for one record using rule_profile thresholds.

    When rule_profile is None (USE_RULE_TABLE=false or during transition), the original
    hardcoded values are used so existing behaviour is fully preserved.
    """
    from app.repositories.rule_repository import _FALLBACK_PROFILE

    profile = rule_profile if rule_profile is not None else _FALLBACK_PROFILE
    heavy_drought_max: float = profile.heavy_drought_max
    waterlogging_min: float = profile.waterlogging_min
    device_fault_water20: float = profile.device_fault_water20
    device_fault_t20: float = profile.device_fault_t20
    rule_version: str = profile.rule_version

    water20 = _safe_float(record.get("water20cm")) or 0.0
    t20 = _safe_float(record.get("t20cm")) or 0.0

    if water20 == device_fault_water20 and t20 == device_fault_t20:
        return {
            "soil_status": "device_fault",
            "warning_level": "device_fault",
            "display_label": "设备故障",
            "risk_score": 100.0,
            "rule_version": rule_version,
        }
    if water20 < heavy_drought_max:
        return {
            "soil_status": "heavy_drought",
            "warning_level": "heavy_drought",
            "display_label": "重旱",
            "risk_score": round(90 + (heavy_drought_max - water20), 2),
            "rule_version": rule_version,
        }
    if water20 >= waterlogging_min:
        return {
            "soil_status": "waterlogging",
            "warning_level": "waterlogging",
            "display_label": "涝渍",
            "risk_score": round(80 + (water20 - waterlogging_min), 2),
            "rule_version": rule_version,
        }
    return {
        "soil_status": "not_triggered",
        "warning_level": "none",
        "display_label": "未达到预警条件",
        "risk_score": round(max(0.0, 70 - abs(water20 - 85) / 2), 2),
        "rule_version": rule_version,
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
    rule_profile: Any = None  # SoilRuleProfile | None — injected by ToolExecutorService

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

    @staticmethod
    def _soil_select_columns_sql() -> str:
        """Return the shared SELECT column list for soil-record queries."""
        return """
        SELECT id, sn, gatewayid, sensorid, unitid, city, county,
               DATE_FORMAT(time, '%Y-%m-%d %H:%i:%s') AS time,
               DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
               water20cm, water40cm, water60cm, water80cm, t20cm, t40cm, t60cm, t80cm,
               water20cmfieldstate, water40cmfieldstate, water60cmfieldstate, water80cmfieldstate,
               t20cmfieldstate, t40cmfieldstate, t60cmfieldstate, t80cmfieldstate,
               lat, lon, source_file, source_sheet, source_row
        FROM fact_soil_moisture
        """.strip()

    @staticmethod
    def _normalize_sql_literal(value: Any) -> str:
        """Normalize a Python value into a SQL literal for audit output."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    @staticmethod
    def _filter_specs(
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[tuple[str, str, str, Any]]:
        """Return the optional filter specifications used by record queries."""
        return [
            ("city", "=", "city", city),
            ("county", "=", "county", county),
            ("sn", "=", "sn", sn),
            ("create_time", ">=", "start_time", start_time),
            ("create_time", "<=", "end_time", end_time),
        ]

    def _build_filter_records_query_pyformat(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> tuple[str, tuple[Any, ...]]:
        """Build the pyformat SQL query and parameters for record filtering."""
        clauses: list[str] = []
        params: list[Any] = []
        for column_name, operator, _param_name, value in self._filter_specs(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        ):
            if value is None:
                continue
            clauses.append(f"{column_name} {operator} %s")
            params.append(value)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        select_sql = self._soil_select_columns_sql().replace("%", "%%")
        sql = f"""
        {select_sql}
        {where_sql}
        ORDER BY create_time DESC
        {limit_sql}
        """
        return sql, tuple(params)

    def _build_filter_records_query_named(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Build the named-parameter SQL used for audit rendering."""
        clauses: list[str] = []
        params: dict[str, Any] = {}
        for column_name, operator, param_name, value in self._filter_specs(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        ):
            if value is None:
                continue
            clauses.append(f"{column_name} {operator} :{param_name}")
            params[param_name] = value
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        sql = f"""
        {self._soil_select_columns_sql()}
        {where_sql}
        ORDER BY create_time DESC
        {limit_sql}
        """
        return sql, params

    def build_filter_records_audit_sql(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> str:
        """Render the filtered record SQL with normalized literals for audit logs."""
        clauses: list[str] = []
        for column_name, operator, _param_name, value in self._filter_specs(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        ):
            if value is None:
                continue
            clauses.append(f"{column_name} {operator} {self._normalize_sql_literal(value)}")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        return (
            f"{self._soil_select_columns_sql()}\n"
            f"{where_sql}\n"
            "ORDER BY create_time DESC\n"
            f"{limit_sql}"
        ).strip()

    def latest_records(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return latest records synchronously for legacy callers."""
        return self.filter_records(limit=limit)

    async def latest_records_async(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return latest records through the async query path."""
        return await self.filter_records_async(limit=limit)

    def filter_records(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Filter soil facts with optional region/device/time predicates."""
        connection = self._connect()
        try:
            sql, params = self._build_filter_records_query_pyformat(
                city=city,
                county=county,
                sn=sn,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [{**row, **_evaluate_record_status(row, self.rule_profile)} for row in rows]
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询失败，已禁止使用种子数据兜底：{exc}") from exc
        finally:
            connection.close()

    async def filter_records_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Async wrapper that prefers SQLAlchemy async engine and falls back to a thread."""
        async_rows = await self._filter_records_with_async_engine(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        if async_rows is not None:
            return async_rows
        return await asyncio.to_thread(
            self.filter_records,
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def _filter_records_with_async_engine(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
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
            sql_text, params = self._build_filter_records_query_named(
                city=city,
                county=county,
                sn=sn,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
            sql = text(sql_text)
            async with engine.connect() as connection:
                result = await connection.execute(sql, params)
                rows = [dict(row._mapping) for row in result]
                return [{**row, **_evaluate_record_status(row, self.rule_profile)} for row in rows]
        except Exception:
            return None
        finally:
            await engine.dispose()

    def latest_record_by_sn(self, sn: str) -> dict[str, Any] | None:
        """Return the newest record for one device SN."""
        records = self.filter_records(sn=sn, limit=1)
        return records[0] if records else None

    def latest_business_time(self) -> str:
        """Return latest `create_time` from facts, not the current wall clock."""
        records = self.filter_records(limit=1)
        return str(records[0].get("create_time")) if records else "暂无"

    async def latest_business_time_async(self) -> str:
        """Async latest-business-time lookup used by time resolution."""
        records = await self.filter_records_async(limit=1)
        return str(records[0].get("create_time")) if records else "暂无"

    def region_alias_rows(self) -> list[dict[str, Any]]:
        """Return enabled region alias mappings for parser normalization."""
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT alias_name, canonical_name, region_level, parent_city_name, alias_source
                    FROM region_alias
                    WHERE enabled = 1
                    ORDER BY alias_name ASC, canonical_name ASC
                    """
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as exc:
            message = str(exc)
            if "region_alias" in message and ("1146" in message or "doesn't exist" in message):
                return []
            raise DatabaseQueryError(f"MySQL 查询地区别名失败，已禁止使用种子数据兜底：{exc}") from exc
        finally:
            connection.close()

    async def region_alias_rows_async(self) -> list[dict[str, Any]]:
        """Async wrapper for region alias lookup."""
        return await asyncio.to_thread(self.region_alias_rows)

    def known_region_names(self) -> set[str]:
        """Return known city/county names observed in the fact table."""
        names = set()
        for record in self.filter_records():
            if record.get("city"):
                names.add(record["city"])
            if record.get("county"):
                names.add(record["county"])
        return names

    async def known_region_names_async(self) -> set[str]:
        """Async variant of known-region discovery."""
        records = await self.filter_records_async()
        names = set()
        for record in records:
            if record.get("city"):
                names.add(record["city"])
            if record.get("county"):
                names.add(record["county"])
        return names

    def region_exists(self, region_name: str) -> bool:
        """Return whether a region name appears in known fact records."""
        return region_name in self.known_region_names()

    async def region_exists_async(self, region_name: str) -> bool:
        """Async region existence check."""
        return region_name in await self.known_region_names_async()

    def device_exists(self, sn: str) -> bool:
        """Return whether a device SN appears in known fact records."""
        return any(record.get("sn") == sn for record in self.filter_records())

    async def device_exists_async(self, sn: str) -> bool:
        """Async device existence check."""
        return any(record.get("sn") == sn for record in await self.filter_records_async())

    def region_record_count(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
    ) -> int:
        """Count records matching one region combination."""
        return len(self.filter_records(city=city, county=county))

    def device_record_count(self, sn: str) -> int:
        """Count records for one device SN."""
        return len(self.filter_records(sn=sn))

    async def region_record_count_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
    ) -> int:
        """Async region record count used by SQL-07 fallback checks."""
        return len(await self.filter_records_async(city=city, county=county))

    async def device_record_count_async(self, sn: str) -> int:
        """Async device record count used by SQL-07 fallback checks."""
        return len(await self.filter_records_async(sn=sn))

    def period_record_summary(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Return count and latest create time for a fallback time-period check."""
        records = self.filter_records(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        )
        latest_create_time = max((str(item.get("create_time") or "") for item in records), default=None)
        return {
            "period_record_count": len(records),
            "latest_create_time": latest_create_time or self.latest_business_time(),
        }

    async def period_record_summary_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Async period summary used by fallback existence diagnostics."""
        records = await self.filter_records_async(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        )
        latest_create_time = max((str(item.get("create_time") or "") for item in records), default=None)
        return {
            "period_record_count": len(records),
            "latest_create_time": latest_create_time or await self.latest_business_time_async(),
        }

    def warning_template_text(self) -> str:
        """Return the default warning template text for rendering services."""
        return DEFAULT_WARNING_TEMPLATE_TEXT

    def evaluate_status(self, record: dict[str, Any]) -> dict[str, Any]:
        """Expose built-in record status evaluation for dashboard summaries."""
        return _evaluate_record_status(record)

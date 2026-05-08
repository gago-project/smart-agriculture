"""MySQL-backed repository for soil-moisture facts."""

from __future__ import annotations


import asyncio
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

from app.db.mysql import MySQLDatabase
from app.services.warning_predicate_service import WarningPredicateService


DEFAULT_WARNING_TEMPLATE_TEXT = "{year} 年 {month} 月 {day} 日 {hour} 时 {city} {county} SN 编号 {sn} 土壤墒情仪监测到相对含水量 {water20cm}%，预警等级 {warning_level}，请大田/设施大棚/林果相关主体关注！"


class DatabaseUnavailableError(RuntimeError):
    """Raised when MySQL cannot be configured or connected."""


class DatabaseQueryError(RuntimeError):
    """Raised when a configured MySQL query fails."""


@dataclass
class SoilRepository:
    """Repository that exposes read-only soil fact queries for the Agent."""

    mysql_host: str | None = None
    mysql_port: int | None = None
    mysql_database: str | None = None
    mysql_user: str | None = None
    mysql_password: str | None = None
    async_database: MySQLDatabase | None = None
    warning_predicate_service: WarningPredicateService = field(default_factory=WarningPredicateService)
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
               lat, lon
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

    def _warning_select_columns_sql(
        self,
        *,
        rule_row: dict[str, Any] | None,
        time_column: str = "create_time",
    ) -> str:
        return self._soil_select_columns_sql().replace(
            "\n        FROM fact_soil_moisture",
            f",\n               {self._warning_case_sql(rule_row=rule_row, time_column=time_column)} AS warning_level\n"
            "        FROM fact_soil_moisture",
        )

    def _build_filter_warning_records_query_pyformat(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> tuple[str, tuple[Any, ...]]:
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
        clauses.append(
            self._pyformat_safe_sql_fragment(
                self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type)
            )
        )
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        sql = f"""
        {self._warning_select_columns_sql(rule_row=rule_row).replace("%", "%%")}
        {where_sql}
        ORDER BY create_time DESC
        {limit_sql}
        """
        return sql, tuple(params)

    def build_filter_warning_records_audit_sql(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> str:
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
        clauses.append(self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type))
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        return (
            f"{self._warning_select_columns_sql(rule_row=rule_row)}\n"
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
                return [dict(row) for row in rows]
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

    def filter_warning_records(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            sql, params = self._build_filter_warning_records_query_pyformat(
                city=city,
                county=county,
                sn=sn,
                start_time=start_time,
                end_time=end_time,
                warning_type=warning_type,
                limit=limit,
                rule_row=rule_row,
            )
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 预警记录过滤失败：{exc}") from exc
        finally:
            connection.close()

    async def filter_warning_records_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self.filter_warning_records,
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
            limit=limit,
            rule_row=rule_row,
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
                return rows
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

    def region_alias_version(self) -> str:
        """Return a version token for enabled region_alias rows."""
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      COALESCE(DATE_FORMAT(MAX(updated_at), '%Y-%m-%d %H:%i:%s'), '') AS max_updated_at,
                      COUNT(*) AS row_count
                    FROM region_alias
                    WHERE enabled = 1
                    """
                )
                row = cursor.fetchone() or {}
                return f"{row.get('max_updated_at') or ''}|{int(row.get('row_count') or 0)}"
        except Exception as exc:
            message = str(exc)
            if "region_alias" in message and ("1146" in message or "doesn't exist" in message):
                return "|0"
            raise DatabaseQueryError(f"MySQL 查询地区别名版本失败：{exc}") from exc
        finally:
            connection.close()

    async def region_alias_version_async(self) -> str:
        """Async wrapper for region alias version lookup."""
        return await asyncio.to_thread(self.region_alias_version)

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

    @staticmethod
    def build_warning_rule_audit_sql(rule_code: str = "soil_warning_v1") -> str:
        """Return the fixed SQL used to read the active warning rule."""
        normalized = SoilRepository._normalize_sql_literal(rule_code)
        return (
            "SELECT rule_code, rule_name, rule_scope, rule_definition_json, enabled,\n"
            "       DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updated_at\n"
            "FROM metric_rule\n"
            f"WHERE enabled = 1 AND rule_code = {normalized}\n"
            "ORDER BY updated_at DESC\n"
            "LIMIT 1"
        )

    def warning_rule_row(self, rule_code: str = "soil_warning_v1") -> dict[str, Any] | None:
        """Return the active warning-rule row from `metric_rule` without hardcoded fallback."""
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rule_code, rule_name, rule_scope, rule_definition_json, enabled,
                           DATE_FORMAT(updated_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS updated_at
                    FROM metric_rule
                    WHERE enabled = 1 AND rule_code = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (rule_code,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询预警规则失败：{exc}") from exc
        finally:
            connection.close()

    async def warning_rule_row_async(self, rule_code: str = "soil_warning_v1") -> dict[str, Any] | None:
        """Async wrapper for warning-rule lookup."""
        return await asyncio.to_thread(self.warning_rule_row, rule_code)

    @staticmethod
    def is_warning_level_active(
        warning_level: str,
        rule_definition: dict,
        check_date: "datetime.date | None" = None,
    ) -> bool:
        """Return False if warning_level is suspended on check_date per seasonal_overrides.

        Reads the ``seasonal_overrides`` array from rule_definition_json and checks
        whether the given warning_level appears in any override whose period contains
        check_date.  Defaults to today when check_date is None.
        """
        import datetime

        date = check_date or datetime.date.today()
        for override in rule_definition.get("seasonal_overrides") or []:
            period = override.get("period") or {}
            ms, ds = period.get("month_start"), period.get("day_start")
            me, de = period.get("month_end"), period.get("day_end")
            if None in (ms, ds, me, de):
                continue
            try:
                start = datetime.date(date.year, int(ms), int(ds))
                end = datetime.date(date.year, int(me), int(de))
            except ValueError:
                continue
            if start <= date <= end:
                if warning_level in (override.get("suspended_warning_levels") or []):
                    return False
        return True

    @staticmethod
    def build_warning_template_audit_sql(domain: str = "soil_moisture") -> str:
        """Return the fixed SQL used to read the latest enabled warning template."""
        normalized = SoilRepository._normalize_sql_literal(domain)
        return (
            "SELECT template_id, domain, warning_type, audience, template_name, template_text,\n"
            "       required_fields_json, version, enabled,\n"
            "       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,\n"
            "       DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updated_at\n"
            "FROM warning_template\n"
            f"WHERE enabled = 1 AND domain = {normalized}\n"
            "ORDER BY updated_at DESC\n"
            "LIMIT 1"
        )

    def warning_template_row(self, domain: str = "soil_moisture") -> dict[str, Any] | None:
        """Return the latest enabled warning template row from `warning_template`."""
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT template_id, domain, warning_type, audience, template_name, template_text,
                           required_fields_json, version, enabled,
                           DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS created_at,
                           DATE_FORMAT(updated_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS updated_at
                    FROM warning_template
                    WHERE enabled = 1 AND domain = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (domain,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询预警模板失败：{exc}") from exc
        finally:
            connection.close()

    async def warning_template_row_async(self, domain: str = "soil_moisture") -> dict[str, Any] | None:
        """Async wrapper for warning-template lookup."""
        return await asyncio.to_thread(self.warning_template_row, domain)

    def warning_template_text(self) -> str:
        """Return the default warning template text for rendering services."""
        return DEFAULT_WARNING_TEMPLATE_TEXT

    @staticmethod
    def build_total_soil_device_count_audit_sql(
        city: str | None = None,
        county: str | None = None,
    ) -> str:
        clauses = ["type = '土壤墒情仪'"]
        normalized_city = SoilRepository._normalize_city_name(city)
        if normalized_city:
            clauses.append(f"city = {SoilRepository._normalize_sql_literal(normalized_city)}")
        if county:
            clauses.append(f"county = {SoilRepository._normalize_sql_literal(county)}")
        return "SELECT COUNT(*) AS total_count FROM subject_device_record WHERE " + " AND ".join(clauses)

    def total_soil_device_count(
        self,
        city: str | None = None,
        county: str | None = None,
    ) -> int | None:
        normalized_city = self._normalize_city_name(city)
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT COUNT(*) AS total_count FROM subject_device_record WHERE type = %s"
                params: list[Any] = ["土壤墒情仪"]
                if normalized_city:
                    sql += " AND city = %s"
                    params.append(normalized_city)
                if county:
                    sql += " AND county = %s"
                    params.append(county)
                cursor.execute(sql, tuple(params))
                row = cursor.fetchone()
                return int(row.get("total_count") or 0) if row else None
        except Exception as exc:
            message = str(exc)
            if "subject_device_record" in message and ("1146" in message or "doesn't exist" in message):
                return None
            raise DatabaseQueryError(f"MySQL 查询设备台账失败：{exc}") from exc
        finally:
            connection.close()

    async def total_soil_device_count_async(
        self,
        city: str | None = None,
        county: str | None = None,
    ) -> int | None:
        return await asyncio.to_thread(self.total_soil_device_count, city, county)

    @staticmethod
    def _normalize_city_name(city: str | None) -> str | None:
        if city is None:
            return None
        normalized = str(city).strip()
        if not normalized:
            return None
        if normalized.endswith("市") or normalized.endswith("港市"):
            return normalized
        return f"{normalized}市"

    @staticmethod
    def build_soil_device_city_distribution_audit_sql() -> str:
        return (
            "SELECT city, COUNT(*) AS device_count\n"
            "FROM subject_device_record\n"
            "WHERE type = '土壤墒情仪'\n"
            "GROUP BY city\n"
            "ORDER BY FIELD(city, '南京市','无锡市','常州市','苏州市','镇江市',"
            "'南通市','扬州市','泰州市','徐州市','连云港市','淮安市','盐城市','宿迁市')"
        )

    def soil_device_city_distribution(self) -> list[dict[str, Any]] | None:
        city_order = [
            "南京市",
            "无锡市",
            "常州市",
            "苏州市",
            "镇江市",
            "南通市",
            "扬州市",
            "泰州市",
            "徐州市",
            "连云港市",
            "淮安市",
            "盐城市",
            "宿迁市",
        ]
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT city, COUNT(*) AS device_count "
                    "FROM subject_device_record "
                    "WHERE type = %s "
                    "GROUP BY city",
                    ("土壤墒情仪",),
                )
                rows = cursor.fetchall()
            normalized: dict[str, int] = {}
            for row in rows:
                city = self._normalize_city_name(row.get("city"))
                if not city:
                    continue
                normalized[city] = normalized.get(city, 0) + int(row.get("device_count") or 0)
            result = [
                {"city": city, "device_count": normalized.get(city, 0)}
                for city in city_order
                if city in normalized
            ]
            return result if result else None
        except Exception as exc:
            message = str(exc)
            if "subject_device_record" in message and ("1146" in message or "doesn't exist" in message):
                return None
            raise DatabaseQueryError(f"MySQL 查询设备城市分布失败：{exc}") from exc
        finally:
            connection.close()

    async def soil_device_city_distribution_async(self) -> list[dict[str, Any]] | None:
        return await asyncio.to_thread(self.soil_device_city_distribution)

    @staticmethod
    def build_soil_device_county_distribution_audit_sql(city: str) -> str:
        escaped = city.replace("'", "''")
        return (
            "SELECT county, COUNT(*) AS device_count\n"
            "FROM subject_device_record\n"
            "WHERE type = '土壤墒情仪' AND city = "
            f"'{escaped}'\n"
            "GROUP BY county\n"
            "ORDER BY device_count DESC"
        )

    def soil_device_county_distribution(self, city: str) -> list[dict[str, Any]] | None:
        normalized_city = self._normalize_city_name(city)
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT county, COUNT(*) AS device_count "
                    "FROM subject_device_record "
                    "WHERE type = %s AND city = %s "
                    "GROUP BY county "
                    "ORDER BY device_count DESC",
                    ("土壤墒情仪", normalized_city),
                )
                rows = cursor.fetchall()
            if not rows:
                return None
            return [
                {
                    "county": row.get("county") or "（未知）",
                    "device_count": int(row.get("device_count") or 0),
                }
                for row in rows
            ]
        except Exception as exc:
            message = str(exc)
            if "subject_device_record" in message and ("1146" in message or "doesn't exist" in message):
                return None
            raise DatabaseQueryError(f"MySQL 查询设备县区分布失败：{exc}") from exc
        finally:
            connection.close()

    async def soil_device_county_distribution_async(self, city: str) -> list[dict[str, Any]] | None:
        return await asyncio.to_thread(self.soil_device_county_distribution, city)

    def _warning_rule_row_or_raise(self, rule_row: dict[str, Any] | None) -> dict[str, Any]:
        active_rule = rule_row or self.warning_rule_row()
        if not active_rule:
            raise DatabaseQueryError("预警规则不可用，无法执行预警查询。")
        return active_rule

    def _warning_filter_sql(
        self,
        *,
        rule_row: dict[str, Any] | None,
        warning_type: str | None = None,
        time_column: str = "create_time",
    ) -> str:
        active_rule = self._warning_rule_row_or_raise(rule_row)
        return self.warning_predicate_service.build_sql_predicate(
            rule_row=active_rule,
            warning_type=warning_type,
            time_column=time_column,
        )

    def _warning_case_sql(
        self,
        *,
        rule_row: dict[str, Any] | None,
        time_column: str = "create_time",
        default_label: str = "normal",
    ) -> str:
        active_rule = self._warning_rule_row_or_raise(rule_row)
        return self.warning_predicate_service.build_warning_case_expression(
            rule_row=active_rule,
            time_column=time_column,
            default_label=default_label,
        )

    @staticmethod
    def _pyformat_safe_sql_fragment(fragment: str) -> str:
        return str(fragment or "").replace("%", "%%")

    def _warning_record_select_sql(
        self,
        *,
        rule_row: dict[str, Any] | None,
        escape_percent_for_pyformat: bool = False,
    ) -> str:
        warning_case_sql = self._warning_case_sql(rule_row=rule_row)
        sql = (
            "SELECT sn, city, county,\n"
            "       DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,\n"
            "       water20cm, water40cm,\n"
            f"       {warning_case_sql} AS warning_level\n"
            "FROM fact_soil_moisture"
        )
        if escape_percent_for_pyformat:
            return sql.replace("%", "%%")
        return sql

    def build_warning_records_audit_sql(
        self,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int = 50,
        rule_row: dict[str, Any] | None = None,
    ) -> str:
        clauses: list[str] = []
        if city:
            clauses.append(f"city = {SoilRepository._normalize_sql_literal(city)}")
        if county:
            clauses.append(f"county = {SoilRepository._normalize_sql_literal(county)}")
        if sn:
            clauses.append(f"sn = {SoilRepository._normalize_sql_literal(sn)}")
        if start_time:
            clauses.append(f"create_time >= {SoilRepository._normalize_sql_literal(start_time)}")
        if end_time:
            clauses.append(f"create_time <= {SoilRepository._normalize_sql_literal(end_time)}")
        clauses.append(
            self._pyformat_safe_sql_fragment(
                self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type)
            )
        )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return (
            f"{self._warning_record_select_sql(rule_row=rule_row)}\n"
            f"{where}\n"
            "ORDER BY create_time DESC\n"
            f"LIMIT {int(limit)}"
        )

    def query_warning_records(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int = 50,
        rule_row: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for col, op, val in [
            ("city", "=", city),
            ("county", "=", county),
            ("sn", "=", sn),
            ("create_time", ">=", start_time),
            ("create_time", "<=", end_time),
        ]:
            if val is not None:
                clauses.append(f"{col} {op} %s")
                params.append(val)

        clauses.append(
            self._pyformat_safe_sql_fragment(
                self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type)
            )
        )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        select_sql = self._warning_record_select_sql(
            rule_row=rule_row,
            escape_percent_for_pyformat=True,
        )
        sql = f"""
        {select_sql}
        {where}
        ORDER BY create_time DESC
        LIMIT %s
        """
        params.append(int(limit))

        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询预警记录失败：{exc}") from exc
        finally:
            connection.close()

    async def query_warning_records_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        limit: int = 50,
        rule_row: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self.query_warning_records,
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
            limit=limit,
            rule_row=rule_row,
        )

    def build_warning_group_audit_sql(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> str:
        warning_case_sql = self._warning_case_sql(rule_row=rule_row)
        warning_filter_sql = self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type)
        clauses: list[str] = []
        if city:
            clauses.append(f"city = {SoilRepository._normalize_sql_literal(city)}")
        if county:
            clauses.append(f"county = {SoilRepository._normalize_sql_literal(county)}")
        if sn:
            clauses.append(f"sn = {SoilRepository._normalize_sql_literal(sn)}")
        if start_time:
            clauses.append(f"create_time >= {SoilRepository._normalize_sql_literal(start_time)}")
        if end_time:
            clauses.append(f"create_time <= {SoilRepository._normalize_sql_literal(end_time)}")
        clauses.append(warning_filter_sql)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return (
            "SELECT city, county,\n"
            "       SUM(warning_level = 'heavy_drought') AS heavy_drought_count,\n"
            "       SUM(warning_level = 'waterlogging') AS waterlogging_count,\n"
            "       SUM(warning_level = 'device_fault') AS device_fault_count,\n"
            "       COUNT(*) AS total_count,\n"
            "       DATE_FORMAT(MAX(create_time), '%Y-%m-%d %H:%i:%s') AS latest_create_time\n"
            "FROM (\n"
            "    SELECT city, county, create_time,\n"
            f"           {warning_case_sql} AS warning_level\n"
            "    FROM fact_soil_moisture\n"
            f"    {where_sql}\n"
            ") AS warning_rows\n"
            "GROUP BY city, county\n"
            "ORDER BY total_count DESC, latest_create_time DESC, city ASC, county ASC"
        )

    def query_warning_group_by_region(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for col, op, val in [
            ("city", "=", city),
            ("county", "=", county),
            ("sn", "=", sn),
            ("create_time", ">=", start_time),
            ("create_time", "<=", end_time),
        ]:
            if val is not None:
                clauses.append(f"{col} {op} %s")
                params.append(val)
        clauses.append(
            self._pyformat_safe_sql_fragment(
                self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type)
            )
        )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        warning_case_sql = self._pyformat_safe_sql_fragment(self._warning_case_sql(rule_row=rule_row))
        sql = f"""
        SELECT city, county,
               SUM(warning_level = 'heavy_drought') AS heavy_drought_count,
               SUM(warning_level = 'waterlogging') AS waterlogging_count,
               SUM(warning_level = 'device_fault') AS device_fault_count,
               COUNT(*) AS total_count,
               DATE_FORMAT(MAX(create_time), '%%Y-%%m-%%d %%H:%%i:%%s') AS latest_create_time
        FROM (
            SELECT city, county, create_time,
                   {warning_case_sql} AS warning_level
            FROM fact_soil_moisture
            {where}
        ) AS warning_rows
        GROUP BY city, county
        ORDER BY total_count DESC, latest_create_time DESC, city ASC, county ASC
        """
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 查询预警区域分布失败：{exc}") from exc
        finally:
            connection.close()

    async def query_warning_group_by_region_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self.query_warning_group_by_region,
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
            rule_row=rule_row,
        )

    @staticmethod
    def build_warning_disposal_audit_sql(
        city: str | None = None,
        county: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> str:
        clauses = ["pub_status IN (1,2,3,4)"]
        if city:
            clauses.append(f"city = {SoilRepository._normalize_sql_literal(city)}")
        if county:
            clauses.append(f"county = {SoilRepository._normalize_sql_literal(county)}")
        if start_time:
            clauses.append(f"warn_time >= {SoilRepository._normalize_sql_literal(start_time)}")
        if end_time:
            clauses.append(f"warn_time <= {SoilRepository._normalize_sql_literal(end_time)}")
        where = "WHERE " + " AND ".join(clauses)
        return (
            "SELECT\n"
            "  COUNT(*) AS total,\n"
            "  SUM(pub_status = 3) AS status_done,\n"
            "  SUM(pub_status = 1) AS status_pending,\n"
            "  SUM(pub_status = 4) AS status_overtime_done,\n"
            "  SUM(pub_status = 2) AS status_overtime_pending\n"
            "FROM warning_disposal_record\n"
            f"{where}"
        )

    def query_warning_disposal_stats(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        # warning_disposal_record is imported from the soil-only disposal workbook subset
        # (warn_type='墒情预警'), so querying this table directly preserves the true
        # business counts even when the device ledger is temporarily incomplete.
        clauses: list[str] = ["pub_status IN (1,2,3,4)"]
        params: list[Any] = []
        for column, value in [("city", city), ("county", county)]:
            if value:
                clauses.append(f"{column} = %s")
                params.append(value)
        if start_time:
            clauses.append("warn_time >= %s")
            params.append(start_time)
        if end_time:
            clauses.append("warn_time <= %s")
            params.append(end_time)
        where = "WHERE " + " AND ".join(clauses)
        sql = f"""
        SELECT
            COUNT(*) AS total,
            SUM(pub_status = 3) AS status_done,
            SUM(pub_status = 1) AS status_pending,
            SUM(pub_status = 4) AS status_overtime_done,
            SUM(pub_status = 2) AS status_overtime_pending
        FROM warning_disposal_record
        {where}
        """
        empty_stats = {
            "total": 0,
            "已处理": 0,
            "待处理": 0,
            "超时已处理": 0,
            "超时待处理": 0,
        }
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                row = cursor.fetchone()
            if not row:
                return empty_stats
            return {
                "total": int(row.get("total") or 0),
                "已处理": int(row.get("status_done") or 0),
                "待处理": int(row.get("status_pending") or 0),
                "超时已处理": int(row.get("status_overtime_done") or 0),
                "超时待处理": int(row.get("status_overtime_pending") or 0),
            }
        except Exception as exc:
            message = str(exc)
            if "warning_disposal_record" in message and ("1146" in message or "doesn't exist" in message):
                return empty_stats
            raise DatabaseQueryError(f"MySQL 查询预警处置统计失败：{exc}") from exc
        finally:
            connection.close()

    async def query_warning_disposal_stats_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.query_warning_disposal_stats,
            city=city,
            county=county,
            start_time=start_time,
            end_time=end_time,
        )

    def count_warning_records_by_region(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clauses: list[str] = []
        params: list[Any] = []
        if city:
            clauses.append("city = %s")
            params.append(city)
        if county:
            clauses.append("county = %s")
            params.append(county)
        if sn:
            clauses.append("sn = %s")
            params.append(sn)
        if start_time:
            clauses.append("create_time >= %s")
            params.append(start_time)
        if end_time:
            clauses.append("create_time <= %s")
            params.append(end_time)
        clauses.append(
            self._pyformat_safe_sql_fragment(
                self._warning_filter_sql(rule_row=rule_row, warning_type=warning_type)
            )
        )

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        warning_case_sql = self._pyformat_safe_sql_fragment(self._warning_case_sql(rule_row=rule_row))
        sql_total = f"SELECT COUNT(*) AS cnt FROM fact_soil_moisture {where}"
        sql_by_level = f"""
        SELECT
            {warning_case_sql} AS warning_level,
            COUNT(*) AS cnt
        FROM fact_soil_moisture {where}
        GROUP BY warning_level
        """
        connection = self._connect()
        try:
            result: dict[str, Any] = {}
            with connection.cursor() as cursor:
                cursor.execute(sql_total, tuple(params))
                row = cursor.fetchone()
                result["total"] = int(row.get("cnt") or 0) if row else 0

                cursor.execute(sql_by_level, tuple(params))
                level_rows = cursor.fetchall()
                result["by_warning_level"] = {
                    r["warning_level"]: int(r["cnt"] or 0)
                    for r in level_rows
                    if r.get("warning_level") != "normal"
                }
            return result
        except Exception as exc:
            raise DatabaseQueryError(f"MySQL 统计预警记录失败：{exc}") from exc
        finally:
            connection.close()

    async def count_warning_records_by_region_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
        rule_row: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.count_warning_records_by_region,
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
            rule_row=rule_row,
        )

"""Repository helpers for rule repository within the soil agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SoilRuleProfile:
    """Structured warning-threshold values loaded by the rule repository."""

    rule_name: str
    heavy_drought_max: float
    waterlogging_min: float
    device_fault_water20: float
    device_fault_t20: float
    rule_version: str = "hardcoded"


_FALLBACK_PROFILE = SoilRuleProfile(
    rule_name="soil_warning_v1",
    heavy_drought_max=50.0,
    waterlogging_min=150.0,
    device_fault_water20=0.0,
    device_fault_t20=0.0,
    rule_version="hardcoded",
)


class RuleRepository:
    """Repository helper for rule — reads metric_rule table when USE_RULE_TABLE=true."""

    def __init__(
        self,
        mysql_host: str | None = None,
        mysql_port: int | None = None,
        mysql_database: str | None = None,
        mysql_user: str | None = None,
        mysql_password: str | None = None,
    ) -> None:
        self._mysql_host = mysql_host
        self._mysql_port = mysql_port or 3306
        self._mysql_database = mysql_database
        self._mysql_user = mysql_user
        self._mysql_password = mysql_password
        self._use_rule_table = os.getenv("USE_RULE_TABLE", "false").lower() == "true"

    @classmethod
    def from_env(cls) -> "RuleRepository":
        """Build repository from process environment variables."""
        return cls(
            mysql_host=os.getenv("MYSQL_HOST"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_database=os.getenv("MYSQL_DATABASE"),
            mysql_user=os.getenv("MYSQL_USER"),
            mysql_password=os.getenv("MYSQL_PASSWORD"),
        )

    def _connect(self):
        """Open a short-lived PyMySQL connection."""
        import pymysql

        return pymysql.connect(
            host=self._mysql_host,
            port=self._mysql_port,
            user=self._mysql_user,
            password=self._mysql_password,
            database=self._mysql_database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=2,
            read_timeout=3,
            write_timeout=3,
        )

    def _load_from_db(self) -> SoilRuleProfile:
        """Load rule thresholds from metric_rule table; falls back to hardcoded on any error."""
        try:
            connection = self._connect()
        except Exception as exc:
            logger.warning("metric_rule: DB connection failed, using hardcoded thresholds: %s", exc)
            return _FALLBACK_PROFILE

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rule_code, rule_definition_json, updated_at "
                    "FROM metric_rule "
                    "WHERE rule_code = 'soil_warning_v1' AND enabled = 1 "
                    "LIMIT 1"
                )
                row = cursor.fetchone()

            if not row:
                logger.warning("metric_rule: soil_warning_v1 not found, using hardcoded thresholds")
                return _FALLBACK_PROFILE

            rule_def = row["rule_definition_json"]
            if isinstance(rule_def, str):
                rule_def = json.loads(rule_def)

            heavy_drought_max = 50.0
            waterlogging_min = 150.0
            device_fault_water20 = 0.0
            device_fault_t20 = 0.0

            for rule in rule_def.get("rules", []):
                cond = rule.get("condition", "")
                level = rule.get("warning_level", "")
                try:
                    if level == "heavy_drought" and "water20cm <" in cond:
                        heavy_drought_max = float(cond.split("<")[-1].strip())
                    elif level == "waterlogging" and ">=" in cond:
                        waterlogging_min = float(cond.split(">=")[-1].strip())
                except (ValueError, IndexError):
                    pass

            updated_at = str(row.get("updated_at", "")).replace(" ", "T")
            rule_version = f"{row['rule_code']}@{updated_at}"

            profile = SoilRuleProfile(
                rule_name=row["rule_code"],
                heavy_drought_max=heavy_drought_max,
                waterlogging_min=waterlogging_min,
                device_fault_water20=device_fault_water20,
                device_fault_t20=device_fault_t20,
                rule_version=rule_version,
            )
            logger.info("metric_rule loaded: %s (heavy_drought_max=%.1f, waterlogging_min=%.1f)",
                        rule_version, heavy_drought_max, waterlogging_min)
            return profile

        except Exception as exc:
            logger.warning("metric_rule: parse failed, using hardcoded thresholds: %s", exc)
            return _FALLBACK_PROFILE
        finally:
            connection.close()

    async def get_active_rule_profile(self) -> SoilRuleProfile:
        """Return the active soil-warning rule profile.

        Reads metric_rule table when USE_RULE_TABLE=true; otherwise returns hardcoded fallback.
        On any DB error, also falls back to hardcoded so the service never crashes.
        """
        if not self._use_rule_table:
            return _FALLBACK_PROFILE
        return await asyncio.to_thread(self._load_from_db)

    async def get_warning_rule_metadata(self) -> dict[str, Any]:
        """Return flattened warning-rule metadata for service callers."""
        profile = await self.get_active_rule_profile()
        return {
            "rule_name": profile.rule_name,
            "heavy_drought_max": profile.heavy_drought_max,
            "waterlogging_min": profile.waterlogging_min,
            "device_fault_water20": profile.device_fault_water20,
            "device_fault_t20": profile.device_fault_t20,
            "rule_version": profile.rule_version,
        }

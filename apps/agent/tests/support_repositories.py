"""Seed-data helpers and repository test doubles for agent tests."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from app.repositories.soil_repository import DEFAULT_WARNING_TEMPLATE_TEXT, SoilRepository


FACT_INSERT_RE = re.compile(
    r"INSERT INTO fact_soil_moisture\s*\(.+?\)\s*VALUES\s*(?P<values>.+?)(?:ON DUPLICATE KEY UPDATE|;)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_sql_tuple(values_text: str) -> list[str]:
    """Parse one SQL tuple literal into a flat list of string values."""
    return next(csv.reader([values_text], delimiter=",", quotechar="'", skipinitialspace=True))


def _coerce_value(value: str) -> Any:
    """Convert one parsed SQL literal into its Python test value."""
    value = value.strip()
    if value == "NULL":
        return None
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _load_seed_records() -> list[dict[str, Any]]:
    """Load seed soil records from the committed MySQL init SQL."""
    init_dir = Path(__file__).resolve().parents[3] / "infra/mysql/init"
    seed_path = init_dir / "003_insert_soil_data.sql"
    if not seed_path.exists():
        seed_path = init_dir / "002_insert_data.sql"
    seed_sql = seed_path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    for match in FACT_INSERT_RE.finditer(seed_sql):
        values_block = match.group("values").strip().rstrip(";")
        tuple_lines = [line.strip().rstrip(",") for line in values_block.splitlines() if line.strip().startswith("(")]
        for tuple_line in tuple_lines:
            values = [_coerce_value(item) for item in _parse_sql_tuple(tuple_line[1:-1])]
            records.append(
                {
                    "id": values[0],
                    "sn": values[1],
                    "gatewayid": values[2],
                    "sensorid": values[3],
                    "unitid": values[4],
                    "city": values[5],
                    "county": values[6],
                    "time": values[7],
                    "create_time": values[8],
                    "water20cm": values[9],
                    "water40cm": values[10],
                    "water60cm": values[11],
                    "water80cm": values[12],
                    "t20cm": values[13],
                    "t40cm": values[14],
                    "t60cm": values[15],
                    "t80cm": values[16],
                    "water20cmfieldstate": values[17],
                    "water40cmfieldstate": values[18],
                    "water60cmfieldstate": values[19],
                    "water80cmfieldstate": values[20],
                    "t20cmfieldstate": values[21],
                    "t40cmfieldstate": values[22],
                    "t60cmfieldstate": values[23],
                    "t80cmfieldstate": values[24],
                    "lat": values[25],
                    "lon": values[26],
                }
            )
    return records


class SeedSoilRepository(SoilRepository):
    """Repository helper for seed soil."""
    def __init__(self) -> None:
        """Initialize the seed soil repository."""
        super().__init__()
        self.records = _load_seed_records()
        self.extra_region_aliases: list[dict[str, Any]] = []
        self.device_city_distribution_rows = [
            {"city": "南京市", "device_count": 48},
            {"city": "无锡市", "device_count": 36},
            {"city": "常州市", "device_count": 28},
            {"city": "苏州市", "device_count": 74},
            {"city": "镇江市", "device_count": 22},
            {"city": "南通市", "device_count": 42},
            {"city": "扬州市", "device_count": 34},
            {"city": "泰州市", "device_count": 30},
            {"city": "徐州市", "device_count": 58},
            {"city": "连云港市", "device_count": 26},
            {"city": "淮安市", "device_count": 40},
            {"city": "盐城市", "device_count": 52},
            {"city": "宿迁市", "device_count": 38},
        ]
        self.device_county_distribution_rows = {
            "南通市": [
                {"county": "如东县", "device_count": 9},
                {"county": "启东市", "device_count": 8},
                {"county": "如皋市", "device_count": 7},
                {"county": "海安市", "device_count": 6},
                {"county": "海门区", "device_count": 5},
                {"county": "通州区", "device_count": 4},
                {"county": "崇川区", "device_count": 2},
                {"county": "开发区", "device_count": 1},
            ]
        }

    def _connect(self):
        """Return the backing connection used by this repository implementation."""
        return None

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
        """Filter records."""
        records = [
            record
            for record in self.records
            if (not city or record.get("city") == city)
            and (not county or record.get("county") == county)
            and (not sn or record.get("sn") == sn)
            and (not start_time or str(record.get("create_time") or "") >= start_time)
            and (not end_time or str(record.get("create_time") or "") <= end_time)
        ]
        records.sort(key=lambda item: str(item.get("create_time") or ""), reverse=True)
        return records[:limit] if limit else records

    async def filter_records_async(self, **kwargs) -> list[dict[str, Any]]:
        """Filter records async."""
        return self.filter_records(**kwargs)

    def latest_business_time(self) -> str:
        """Return the latest business time."""
        latest_record = max(self.records, key=lambda item: str(item.get("create_time") or ""), default=None)
        return str(latest_record.get("create_time")) if latest_record else "暂无"

    async def latest_business_time_async(self) -> str:
        """Return the latest business time async."""
        return self.latest_business_time()

    def warning_template_text(self) -> str:
        """Handle warning template text on the seed soil repository."""
        return DEFAULT_WARNING_TEMPLATE_TEXT

    def region_alias_rows(self) -> list[dict[str, Any]]:
        """Return region alias rows (only manually-injected extras; auto-generation removed)."""
        return list(self.extra_region_aliases)

    async def region_alias_rows_async(self) -> list[dict[str, Any]]:
        """Return region alias rows async."""
        return self.region_alias_rows()

    def region_alias_version(self) -> str:
        """Return a deterministic alias version token for tests."""
        return f"seed|{len(self.extra_region_aliases)}"

    async def region_alias_version_async(self) -> str:
        """Return alias version token async."""
        return self.region_alias_version()

    def region_record_count(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
    ) -> int:
        """Count records matching one region combination."""
        return len(self.filter_records(city=city, county=county))

    async def region_record_count_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
    ) -> int:
        """Async region record count."""
        return self.region_record_count(city=city, county=county)

    def device_record_count(self, sn: str) -> int:
        """Count records for one device SN."""
        return len(self.filter_records(sn=sn))

    async def device_record_count_async(self, sn: str) -> int:
        """Async device record count."""
        return self.device_record_count(sn=sn)

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
        """Async period summary."""
        return self.period_record_summary(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        )

    def warning_rule_row(self, rule_code: str = "soil_warning_v1") -> dict[str, Any] | None:
        """Return a deterministic warning-rule fixture for unit tests."""
        return {
            "rule_code": rule_code,
            "rule_name": "土壤墒情预警规则",
            "rule_scope": "soil",
            "rule_definition_json": {
                "rules": [
                    {"warning_level": "heavy_drought", "condition": "water20cm < 50"},
                    {"warning_level": "waterlogging", "condition": "water20cm >= 150"},
                    {"warning_level": "device_fault", "condition": "water20cm = 0 and t20cm = 0"},
                ]
            },
            "enabled": 1,
            "updated_at": "2026-04-13 23:59:59",
        }

    async def warning_rule_row_async(self, rule_code: str = "soil_warning_v1") -> dict[str, Any] | None:
        """Async warning-rule fixture lookup."""
        return self.warning_rule_row(rule_code)

    def warning_template_row(self, domain: str = "soil_moisture") -> dict[str, Any] | None:
        """Return a deterministic warning-template fixture for unit tests."""
        return {
            "template_id": "soil_default_warning",
            "domain": domain,
            "warning_type": "soil_moisture",
            "audience": "farmer",
            "template_name": "土壤墒情预警模板",
            "template_text": DEFAULT_WARNING_TEMPLATE_TEXT,
            "required_fields_json": [
                "year",
                "month",
                "day",
                "hour",
                "city",
                "county",
                "sn",
                "water20cm",
                "warning_level",
            ],
            "version": "seed-template-v1",
            "enabled": 1,
            "created_at": "2026-04-13 23:59:59",
            "updated_at": "2026-04-13 23:59:59",
        }

    async def warning_template_row_async(self, domain: str = "soil_moisture") -> dict[str, Any] | None:
        """Async warning-template fixture lookup."""
        return self.warning_template_row(domain)

    def total_soil_device_count(self) -> int | None:
        """Return seed device count (528 土壤墒情仪 devices from subject_device_record fixture)."""
        return 528

    async def total_soil_device_count_async(self) -> int | None:
        """Async wrapper for seed device count."""
        return self.total_soil_device_count()

    def soil_device_city_distribution(self) -> list[dict[str, Any]] | None:
        """Return deterministic city-level device distribution for tests."""
        if not self.device_city_distribution_rows:
            return None
        return [dict(row) for row in self.device_city_distribution_rows]

    async def soil_device_city_distribution_async(self) -> list[dict[str, Any]] | None:
        """Async city-level device distribution for tests."""
        return self.soil_device_city_distribution()

    def soil_device_county_distribution(self, city: str) -> list[dict[str, Any]] | None:
        """Return deterministic county-level device distribution for one city."""
        normalized_city = self._normalize_city_name(city)
        rows = self.device_county_distribution_rows.get(normalized_city or "")
        if not rows:
            return None
        return [dict(row) for row in rows]

    async def soil_device_county_distribution_async(self, city: str) -> list[dict[str, Any]] | None:
        """Async county-level device distribution for tests."""
        return self.soil_device_county_distribution(city)

    @staticmethod
    def _warning_level_for_record(record: dict[str, Any]) -> str | None:
        """Evaluate one seed row with the same threshold contract as the SQL path."""
        water20 = record.get("water20cm")
        t20 = record.get("t20cm")
        if water20 == 0 and t20 == 0:
            return "device_fault"
        if isinstance(water20, (int, float)) and water20 < 50:
            return "heavy_drought"
        if isinstance(water20, (int, float)) and water20 >= 150:
            return "waterlogging"
        return None

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
    ) -> list[dict[str, Any]]:
        """Return seed warning rows using the same SQL-threshold semantics."""
        filtered: list[dict[str, Any]] = []
        for record in self.filter_records(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        ):
            warning_level = self._warning_level_for_record(record)
            if warning_level is None:
                continue
            if warning_type and warning_level != warning_type:
                continue
            filtered.append(
                {
                    "sn": record.get("sn"),
                    "city": record.get("city"),
                    "county": record.get("county"),
                    "create_time": record.get("create_time"),
                    "water20cm": record.get("water20cm"),
                    "water40cm": record.get("water40cm"),
                    "warning_level": warning_level,
                }
            )
        return filtered[:limit]

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
    ) -> list[dict[str, Any]]:
        """Async warning-row query for tests."""
        return self.query_warning_records(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
            limit=limit,
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
    ) -> dict[str, Any]:
        """Count seed warning rows with optional warning-type filtering."""
        rows = self.query_warning_records(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
            limit=len(self.records),
        )
        by_level: dict[str, int] = {}
        for row in rows:
            level = str(row.get("warning_level") or "")
            by_level[level] = by_level.get(level, 0) + 1
        return {
            "total": len(rows),
            "by_warning_level": by_level,
        }

    async def count_warning_records_by_region_async(
        self,
        *,
        city: str | None = None,
        county: str | None = None,
        sn: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        warning_type: str | None = None,
    ) -> dict[str, Any]:
        """Async warning count for tests."""
        return self.count_warning_records_by_region(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            warning_type=warning_type,
        )

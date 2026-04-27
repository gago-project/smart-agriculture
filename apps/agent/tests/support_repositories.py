"""Seed-data helpers and repository test doubles for agent tests."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from app.repositories.soil_repository import DEFAULT_WARNING_TEMPLATE_TEXT, SoilRepository, _evaluate_record_status


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
                    "source_file": values[27],
                    "source_sheet": values[28],
                    "source_row": values[29],
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
        enriched_records = [{**record, **_evaluate_record_status(record)} for record in records]
        enriched_records.sort(key=lambda item: str(item.get("create_time") or ""), reverse=True)
        return enriched_records[:limit] if limit else enriched_records

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

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from app.repositories.soil_repository import DEFAULT_WARNING_TEMPLATE_TEXT, SoilRepository, _evaluate_record_status


FACT_INSERT_RE = re.compile(
    r"INSERT INTO fact_soil_moisture\s*\(.+?\)\s*VALUES\s*(?P<values>.+?)\s*ON DUPLICATE KEY",
    re.IGNORECASE | re.DOTALL,
)


def _parse_sql_tuple(values_text: str) -> list[str]:
    return next(csv.reader([values_text], delimiter=",", quotechar="'", skipinitialspace=True))


def _coerce_value(value: str) -> Any:
    value = value.strip()
    if value == "NULL":
        return None
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _load_seed_records() -> list[dict[str, Any]]:
    seed_path = Path(__file__).resolve().parents[3] / "infra/mysql/init/002_insert_data.sql"
    seed_sql = seed_path.read_text(encoding="utf-8")
    match = FACT_INSERT_RE.search(seed_sql)
    if not match:
        return []
    records: list[dict[str, Any]] = []
    values_block = match.group("values").strip().rstrip(";")
    tuple_lines = [line.strip().rstrip(",") for line in values_block.splitlines() if line.strip().startswith("(")]
    for tuple_line in tuple_lines:
        values = [_coerce_value(item) for item in _parse_sql_tuple(tuple_line[1:-1])]
        records.append(
            {
                "record_id": values[0],
                "batch_id": values[1],
                "device_sn": values[2],
                "device_name": values[6],
                "city_name": values[7],
                "county_name": values[8],
                "town_name": values[9],
                "sample_time": values[10],
                "create_time": values[11],
                "water20cm": values[12],
                "water40cm": values[13],
                "water60cm": values[14],
                "water80cm": values[15],
                "t20cm": values[16],
                "t40cm": values[17],
                "t60cm": values[18],
                "t80cm": values[19],
                "soil_anomaly_type": values[28],
                "soil_anomaly_score": values[29],
                "longitude": values[30],
                "latitude": values[31],
                "source_file": values[32],
                "source_sheet": values[33],
                "source_row": values[34],
            }
        )
    return records


class SeedSoilRepository(SoilRepository):
    def __init__(self) -> None:
        super().__init__()
        self.records = _load_seed_records()

    def _connect(self):
        return None

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
        records = [
            record
            for record in self.records
            if (not city_name or record.get("city_name") == city_name)
            and (not county_name or record.get("county_name") == county_name)
            and (not town_name or record.get("town_name") == town_name)
            and (not device_sn or record.get("device_sn") == device_sn)
            and (not batch_id or record.get("batch_id") == batch_id)
            and (not start_time or str(record.get("sample_time") or "") >= start_time)
            and (not end_time or str(record.get("sample_time") or "") <= end_time)
        ]
        enriched_records = [{**record, **_evaluate_record_status(record)} for record in records]
        enriched_records.sort(key=lambda item: str(item.get("sample_time") or ""), reverse=True)
        return enriched_records[:limit] if limit else enriched_records

    async def filter_records_async(self, **kwargs) -> list[dict[str, Any]]:
        return self.filter_records(**kwargs)

    def latest_batch_id(self) -> str | None:
        latest_record = max(self.records, key=lambda item: str(item.get("sample_time") or ""), default=None)
        return str(latest_record.get("batch_id")) if latest_record else None

    async def latest_batch_id_async(self) -> str | None:
        return self.latest_batch_id()

    def latest_business_time(self) -> str:
        latest_record = max(self.records, key=lambda item: str(item.get("sample_time") or ""), default=None)
        return str(latest_record.get("sample_time")) if latest_record else "暂无"

    async def latest_business_time_async(self) -> str:
        return self.latest_business_time()

    def warning_template_text(self) -> str:
        return DEFAULT_WARNING_TEMPLATE_TEXT

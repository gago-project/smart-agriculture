"""Tool executor for raw-only soil fact queries."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


MAX_TOP_N = 20
MAX_RANKING_DAYS = 365
MAX_COMPARISON_ENTITIES = 5

ALLOWED_TOOLS = {
    "query_soil_summary",
    "query_soil_ranking",
    "query_soil_detail",
    "query_soil_comparison",
    "diagnose_empty_result",
}


class ToolValidationError(ValueError):
    """Raised when LLM-supplied tool parameters fail safety validation."""


class ToolExecutorService:
    """Validate and execute one tool call against raw `fact_soil_moisture` data."""

    def __init__(self, repository: Any, rule_repository: Any | None = None) -> None:
        self.repository = repository
        self._rule_repository = rule_repository

    async def execute(
        self,
        *,
        tool_name: str,
        tool_args: dict[str, Any],
        entity_confidence: str = "high",
    ) -> dict[str, Any]:
        if tool_name not in ALLOWED_TOOLS:
            raise ToolValidationError(f"Unknown tool: {tool_name!r}. Allowed: {sorted(ALLOWED_TOOLS)}")
        self._validate_time_params(tool_args)
        self._validate_tool_specific(tool_name, tool_args)

        if tool_name == "query_soil_summary":
            return await self._execute_summary(tool_args, entity_confidence=entity_confidence)
        if tool_name == "query_soil_ranking":
            return await self._execute_ranking(tool_args, entity_confidence=entity_confidence)
        if tool_name == "query_soil_detail":
            return await self._execute_detail(tool_args, entity_confidence=entity_confidence)
        if tool_name == "query_soil_comparison":
            return await self._execute_comparison(tool_args, entity_confidence=entity_confidence)
        return await self._execute_diagnose(tool_args)

    async def _execute_summary(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]
        output_mode = args.get("output_mode", "normal")

        records = await self.repository.filter_records_async(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        )
        if not records:
            empty_path = await self._auto_diagnose_empty(args, entity_confidence)
            return {
                "entity_type": "device" if sn else "region",
                "entity_name": sn or county or city or "全局",
                "total_records": 0,
                "output_mode": output_mode,
                "time_window": {"start_time": start_time, "end_time": end_time},
                "avg_water20cm": None,
                "device_count": 0,
                "region_count": 0,
                "latest_create_time": None,
                "top_regions": [],
                "empty_result_path": empty_path,
            }

        summary = _aggregate_records(records)
        return {
            "entity_type": "device" if sn else "region",
            "entity_name": sn or county or city or "全局",
            "total_records": summary["record_count"],
            "output_mode": output_mode,
            "time_window": {"start_time": start_time, "end_time": end_time},
            "avg_water20cm": summary["avg_water20cm"],
            "device_count": summary["device_count"],
            "region_count": summary["region_count"],
            "latest_create_time": summary["latest_create_time"],
            "top_regions": _group_region_rows(records)[:5],
        }

    async def _execute_ranking(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        city = args.get("city")
        county = args.get("county")
        start_time = args["start_time"]
        end_time = args["end_time"]
        top_n = min(int(args.get("top_n") or 5), MAX_TOP_N)
        aggregation = args.get("aggregation", "county")

        records = await self.repository.filter_records_async(
            city=city,
            county=county,
            start_time=start_time,
            end_time=end_time,
        )
        if not records:
            empty_path = await self._auto_diagnose_empty(args, entity_confidence)
            return {
                "aggregation": aggregation,
                "top_n": top_n,
                "total_analyzed": 0,
                "time_window": {"start_time": start_time, "end_time": end_time},
                "items": [],
                "empty_result_path": empty_path,
            }

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if aggregation == "city":
                key = str(record.get("city") or "未知")
            elif aggregation == "device":
                key = str(record.get("sn") or "未知")
            else:
                key = str(record.get("county") or record.get("city") or "未知")
            groups[key].append(record)

        items: list[dict[str, Any]] = []
        for name, group_records in groups.items():
            summary = _aggregate_records(group_records)
            item: dict[str, Any] = {
                "name": name,
                "record_count": summary["record_count"],
                "device_count": summary["device_count"],
                "avg_water20cm": summary["avg_water20cm"],
                "latest_create_time": summary["latest_create_time"],
            }
            sample = group_records[0]
            if aggregation == "device":
                item["city"] = sample.get("city")
                item["county"] = sample.get("county")
            elif aggregation == "county":
                item["city"] = sample.get("city")
            items.append(item)

        items.sort(
            key=lambda item: (
                -int(item.get("record_count") or 0),
                -int(item.get("device_count") or 0),
                str(item.get("latest_create_time") or ""),
                str(item.get("name") or ""),
            )
        )
        top_items = items[:top_n]
        for index, item in enumerate(top_items, start=1):
            item["rank"] = index

        return {
            "aggregation": aggregation,
            "top_n": top_n,
            "total_analyzed": len(groups),
            "time_window": {"start_time": start_time, "end_time": end_time},
            "items": top_items,
        }

    async def _execute_detail(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]
        output_mode = args.get("output_mode", "normal")

        records = await self.repository.filter_records_async(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        )
        if not records:
            empty_path = await self._auto_diagnose_empty(args, entity_confidence)
            return {
                "entity_type": "device" if sn else "region",
                "entity_name": sn or county or city or "未知",
                "output_mode": output_mode,
                "record_count": 0,
                "time_window": {"start_time": start_time, "end_time": end_time},
                "latest_record": None,
                "avg_water20cm": None,
                "device_count": 0,
                "region_count": 0,
                "latest_create_time": None,
                "empty_result_path": empty_path,
            }

        summary = _aggregate_records(records)
        latest_record = _slim_record(_latest_record(records))
        return {
            "entity_type": "device" if sn else "region",
            "entity_name": sn or county or city or "未知",
            "output_mode": output_mode,
            "record_count": summary["record_count"],
            "time_window": {"start_time": start_time, "end_time": end_time},
            "latest_record": latest_record,
            "avg_water20cm": summary["avg_water20cm"],
            "device_count": summary["device_count"],
            "region_count": summary["region_count"],
            "latest_create_time": summary["latest_create_time"],
        }

    async def _execute_comparison(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        entity_type = args.get("entity_type", "region")
        entities: list[dict[str, Any]] = list(args.get("entities") or [])
        start_time = args["start_time"]
        end_time = args["end_time"]

        if not entities:
            return {
                "entity_type": entity_type,
                "time_window": {"start_time": start_time, "end_time": end_time},
                "items": [],
                "comparison": [],
                "empty_result_path": "normalize_failed",
            }

        items: list[dict[str, Any]] = []
        for entity in entities:
            canonical_name = str(entity.get("canonical_name") or "")
            level = str(entity.get("level") or "")
            parent_city_name = entity.get("parent_city_name")
            raw_name = str(entity.get("raw_name") or canonical_name or "未知")

            if level == "device":
                kwargs = {"sn": canonical_name}
            elif level == "city":
                kwargs = {"city": canonical_name}
            elif level == "county":
                kwargs = {"county": canonical_name}
            else:
                kwargs = {}

            records = await self.repository.filter_records_async(
                start_time=start_time,
                end_time=end_time,
                **kwargs,
            )
            if not records:
                empty_path = await self._auto_diagnose_empty(
                    {**kwargs, "start_time": start_time, "end_time": end_time},
                    entity_confidence,
                )
                items.append(
                    {
                        "name": canonical_name or raw_name,
                        "entity_type": entity_type,
                        "entity_level": level or entity_type,
                        "parent_city_name": parent_city_name,
                        "record_count": 0,
                        "device_count": 0,
                        "region_count": 0,
                        "avg_water20cm": None,
                        "latest_create_time": None,
                        "empty_result_path": empty_path,
                    }
                )
                continue

            summary = _aggregate_records(records)
            items.append(
                {
                    "name": canonical_name or raw_name,
                    "entity_type": entity_type,
                    "entity_level": level or entity_type,
                    "parent_city_name": parent_city_name,
                    "record_count": summary["record_count"],
                    "device_count": summary["device_count"],
                    "region_count": summary["region_count"],
                    "avg_water20cm": summary["avg_water20cm"],
                    "latest_create_time": summary["latest_create_time"],
                }
            )

        items.sort(
            key=lambda item: (
                -int(item.get("record_count") or 0),
                -int(item.get("device_count") or 0),
                str(item.get("latest_create_time") or ""),
                str(item.get("name") or ""),
            )
        )
        for index, item in enumerate(items, start=1):
            item["rank"] = index

        return {
            "entity_type": entity_type,
            "time_window": {"start_time": start_time, "end_time": end_time},
            "total_entities": len(entities),
            "items": items,
            "comparison": items,
        }

    async def _execute_diagnose(self, args: dict[str, Any]) -> dict[str, Any]:
        scenario = args.get("scenario", "period_exists")
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]

        if scenario == "region_exists":
            count = await self.repository.region_record_count_async(city=city, county=county)
            entity_name = county or city or "未知"
            exists = count > 0
            return {
                "scenario": scenario,
                "entity_type": "region",
                "entity_name": entity_name,
                "entity_exists": exists,
                "diagnosis": "data_exists" if exists else "entity_not_found",
                "record_count_all_time": count,
                "record_count_in_window": None,
                "message": f"地区 {entity_name} {'在系统中存在' if exists else '在系统中不存在，请核对地区名称'}",
            }

        if scenario == "device_exists":
            count = await self.repository.device_record_count_async(sn or "")
            entity_name = sn or "未知"
            exists = count > 0
            return {
                "scenario": scenario,
                "entity_type": "device",
                "entity_name": entity_name,
                "entity_exists": exists,
                "diagnosis": "data_exists" if exists else "entity_not_found",
                "record_count_all_time": count,
                "record_count_in_window": None,
                "message": f"设备 {entity_name} {'在系统中存在' if exists else '在系统中不存在，请核对设备编号'}",
            }

        summary = await self.repository.period_record_summary_async(
            city=city,
            county=county,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
        )
        in_window = summary.get("period_record_count", 0) or 0
        entity_name = sn or county or city or "全域"
        diagnosis = "data_exists" if in_window > 0 else "no_data_in_window"
        return {
            "scenario": scenario,
            "entity_type": "device" if sn else "region",
            "entity_name": entity_name,
            "entity_exists": True,
            "diagnosis": diagnosis,
            "record_count_all_time": None,
            "record_count_in_window": in_window,
            "message": (
                f"时间段 {start_time[:10]} ~ {end_time[:10]} 内"
                f"{'有' if in_window else '没有'} {entity_name} 的数据"
                + (f"，共 {in_window} 条" if in_window else "，可以扩大时间范围或查询其他时段")
            ),
        }

    async def _auto_diagnose_empty(self, args: dict[str, Any], entity_confidence: str) -> str:
        if entity_confidence == "low":
            return "normalize_failed"
        sn = args.get("sn")
        city = args.get("city")
        county = args.get("county")
        if sn:
            count = await self.repository.device_record_count_async(sn)
            return "entity_not_found" if count == 0 else "no_data_in_window"
        count = await self.repository.region_record_count_async(city=city, county=county)
        return "entity_not_found" if count == 0 else "no_data_in_window"

    def _validate_time_params(self, args: dict[str, Any]) -> None:
        for field in ("start_time", "end_time"):
            value = args.get(field)
            if not value:
                raise ToolValidationError(f"Missing required param: {field}")
            try:
                datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise ToolValidationError(f"Invalid datetime format for {field}: {value!r}") from exc

    def _validate_tool_specific(self, tool_name: str, args: dict[str, Any]) -> None:
        day_span = self._day_span(args["start_time"], args["end_time"])

        if tool_name == "query_soil_ranking":
            top_n = int(args.get("top_n") or 5)
            if top_n > MAX_TOP_N:
                raise ToolValidationError(f"top_n {top_n} exceeds maximum {MAX_TOP_N}")
            aggregation = args.get("aggregation", "county")
            if aggregation == "device" and day_span > MAX_RANKING_DAYS:
                raise ToolValidationError(
                    f"time_span {day_span} days exceeds {MAX_RANKING_DAYS} for device ranking"
                )

        if tool_name == "query_soil_comparison":
            entities = args.get("entities") or []
            if not isinstance(entities, list) or len(entities) < 2:
                raise ToolValidationError("query_soil_comparison requires at least 2 entities")
            if len(entities) > MAX_COMPARISON_ENTITIES:
                raise ToolValidationError(
                    f"comparison entities {len(entities)} exceeds maximum {MAX_COMPARISON_ENTITIES}"
                )
            entity_type = args.get("entity_type")
            if entity_type not in ("region", "device"):
                raise ToolValidationError(
                    f"comparison entity_type must be 'region' or 'device', got {entity_type!r}"
                )
            for entity in entities:
                if not isinstance(entity, dict):
                    raise ToolValidationError("comparison entities must be resolver-normalized objects")
                canonical_name = str(entity.get("canonical_name") or "").strip()
                level = str(entity.get("level") or "").strip()
                if not canonical_name:
                    raise ToolValidationError("comparison entity canonical_name is required")
                if entity_type == "device":
                    if level != "device":
                        raise ToolValidationError("device comparison entity level must be 'device'")
                elif level not in ("city", "county"):
                    raise ToolValidationError("region comparison entity level must be 'city' or 'county'")

    @staticmethod
    def _day_span(start_time: str, end_time: str) -> int:
        start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        return max((end.date() - start.date()).days + 1, 1)


def _aggregate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    water_values = [float(record["water20cm"]) for record in records if record.get("water20cm") is not None]
    device_keys = {str(record.get("sn") or "").strip() for record in records if str(record.get("sn") or "").strip()}
    region_keys = {
        (record.get("city"), record.get("county"))
        for record in records
        if record.get("city") or record.get("county")
    }
    latest_create_time = max((str(record.get("create_time") or "") for record in records), default=None)
    return {
        "record_count": len(records),
        "device_count": len(device_keys),
        "region_count": len(region_keys),
        "avg_water20cm": round(sum(water_values) / len(water_values), 2) if water_values else None,
        "latest_create_time": latest_create_time,
    }


def _group_region_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for record in records:
        key = (record.get("city"), record.get("county"))
        bucket = grouped.setdefault(
            key,
            {
                "region": f"{record.get('city') or ''}{record.get('county') or ''}".strip() or "未知",
                "city": record.get("city"),
                "county": record.get("county"),
                "record_count": 0,
                "device_keys": set(),
                "latest_create_time": None,
                "water_values": [],
            },
        )
        bucket["record_count"] += 1
        sn = str(record.get("sn") or "").strip()
        if sn:
            bucket["device_keys"].add(sn)
        timestamp = str(record.get("create_time") or "")
        if timestamp:
            bucket["latest_create_time"] = max(str(bucket.get("latest_create_time") or ""), timestamp)
        if record.get("water20cm") is not None:
            bucket["water_values"].append(float(record["water20cm"]))

    rows = []
    for bucket in grouped.values():
        device_keys = bucket.pop("device_keys")
        water_values = bucket.pop("water_values")
        bucket["device_count"] = len(device_keys)
        bucket["avg_water20cm"] = round(sum(water_values) / len(water_values), 2) if water_values else None
        rows.append(bucket)
    rows.sort(
        key=lambda item: (
            -int(item.get("record_count") or 0),
            -int(item.get("device_count") or 0),
            str(item.get("latest_create_time") or ""),
            str(item.get("region") or ""),
        )
    )
    return rows


def _latest_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda record: str(record.get("sn") or ""))
    ordered.sort(key=lambda record: str(record.get("create_time") or ""), reverse=True)
    return ordered[0]


def _slim_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "sn",
            "city",
            "county",
            "create_time",
            "water20cm",
            "water40cm",
            "water60cm",
            "water80cm",
            "t20cm",
            "t40cm",
            "t60cm",
            "t80cm",
        )
    }


__all__ = ["ToolExecutorService", "ToolValidationError"]

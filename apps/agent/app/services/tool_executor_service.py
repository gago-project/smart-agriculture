"""Tool executor: maps LLM tool-call decisions to structured repository calls.

This is the only place where LLM-supplied parameters touch real data.
Each tool returns problem-oriented structured results, not raw records:
  - query_soil_summary  → aggregated overview stats
  - query_soil_ranking  → sorted TopN list (already aggregated)
  - query_soil_detail   → single entity detail with evidence fields
  - diagnose_empty_result → structured diagnosis (entity vs window)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.repositories.rule_repository import RuleRepository
from app.repositories.soil_repository import SoilRepository, _evaluate_record_status

MAX_TOP_N = 20
MAX_RANKING_DAYS = 365
MAX_ANOMALY_DAYS = 180
MAX_COMPARISON_ENTITIES = 5

ALLOWED_TOOLS = {
    "query_soil_summary",
    "query_soil_ranking",
    "query_soil_detail",
    "query_soil_comparison",
    "diagnose_empty_result",
}

_ALERT_STATUSES = {"heavy_drought", "waterlogging", "device_fault"}


class ToolValidationError(ValueError):
    """Raised when LLM-supplied tool parameters fail safety validation."""


class ToolExecutorService:
    """Validate and execute a single LLM tool call against SoilRepository."""

    def __init__(self, repository: SoilRepository, rule_repository: RuleRepository | None = None) -> None:
        self.repository = repository
        self._rule_repository = rule_repository or RuleRepository.from_env()
        self._rule_profile_loaded = False

    async def _ensure_rule_profile(self) -> None:
        """Load rule profile once and inject into repository (lazy, called before first tool exec)."""
        if not self._rule_profile_loaded:
            profile = await self._rule_repository.get_active_rule_profile()
            self.repository.rule_profile = profile
            self._rule_profile_loaded = True

    async def execute(
        self,
        *,
        tool_name: str,
        tool_args: dict[str, Any],
        entity_confidence: str = "high",
    ) -> dict[str, Any]:
        """Validate params and execute the named tool. Raises ToolValidationError on bad params.

        entity_confidence is passed from ParameterResolverService to inform empty-result diagnosis.
        """
        await self._ensure_rule_profile()
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
        # diagnose_empty_result (internal use only — not exposed in SOIL_TOOLS)
        return await self._execute_diagnose(tool_args)

    # ── per-tool executors ────────────────────────────────────────────────────

    async def _execute_summary(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        """Return aggregated overview stats, not raw records."""
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]
        output_mode = args.get("output_mode", "normal")

        records = await self.repository.filter_records_async(
            city=city, county=county, sn=sn,
            start_time=start_time, end_time=end_time,
        )

        if not records:
            empty_path = await self._auto_diagnose_empty(args, entity_confidence)
            return {
                "total_records": 0,
                "output_mode": output_mode,
                "time_window": {"start_time": start_time, "end_time": end_time},
                "avg_water20cm": None,
                "status_counts": {},
                "alert_count": 0,
                "top_alert_regions": [],
                "empty_result_path": empty_path,
            }

        # Evaluate status for each record
        enriched = [_evaluate_and_merge(r) for r in records]

        water_vals = [float(r["water20cm"]) for r in enriched if r.get("water20cm") is not None]
        avg_water = round(sum(water_vals) / len(water_vals), 2) if water_vals else None

        status_counts: dict[str, int] = defaultdict(int)
        for r in enriched:
            status_counts[r.get("soil_status", "unknown")] += 1

        alert_count = sum(v for k, v in status_counts.items() if k in _ALERT_STATUSES)

        # Top alert regions (county or city level)
        county_alerts: dict[str, int] = defaultdict(int)
        for r in enriched:
            if r.get("soil_status") in _ALERT_STATUSES:
                key = r.get("county") or r.get("city") or "未知"
                county_alerts[key] += 1

        top_alert_regions = [
            {"region": k, "alert_count": v}
            for k, v in sorted(county_alerts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        result: dict[str, Any] = {
            "total_records": len(enriched),
            "output_mode": output_mode,
            "time_window": {"start_time": start_time, "end_time": end_time},
            "avg_water20cm": avg_water,
            "status_counts": dict(status_counts),
            "alert_count": alert_count,
            "top_alert_regions": top_alert_regions,
        }

        if output_mode in ("anomaly_focus", "warning_mode"):
            alert_records = [r for r in enriched if r.get("soil_status") in _ALERT_STATUSES]
            result["alert_records"] = _slim_records(alert_records[:10])

        return result

    async def _execute_ranking(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        """Return sorted TopN list, already aggregated and ranked."""
        city = args.get("city")
        county = args.get("county")
        start_time = args["start_time"]
        end_time = args["end_time"]
        top_n = min(int(args.get("top_n") or 5), MAX_TOP_N)
        aggregation = args.get("aggregation", "county")

        records = await self.repository.filter_records_async(
            city=city, county=county,
            start_time=start_time, end_time=end_time,
        )

        if not records:
            empty_path = await self._auto_diagnose_empty(args, entity_confidence)
            return {
                "aggregation": aggregation,
                "top_n": top_n,
                "total_analyzed": 0,
                "items": [],
                "empty_result_path": empty_path,
            }

        enriched = [_evaluate_and_merge(r) for r in records]

        # Aggregate by dimension
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in enriched:
            if aggregation == "city":
                key = r.get("city") or "未知"
            elif aggregation == "device":
                key = r.get("sn") or "未知"
            else:  # county
                key = r.get("county") or r.get("city") or "未知"
            groups[key].append(r)

        items = []
        for name, group_records in groups.items():
            water_vals = [float(r["water20cm"]) for r in group_records if r.get("water20cm") is not None]
            avg_water = round(sum(water_vals) / len(water_vals), 2) if water_vals else None
            status_counts: dict[str, int] = defaultdict(int)
            for r in group_records:
                status_counts[r.get("soil_status", "unknown")] += 1
            alert_count = sum(v for k, v in status_counts.items() if k in _ALERT_STATUSES)
            dominant_status = max(status_counts.items(), key=lambda x: x[1])[0]

            # Use rule-table risk_score as primary sort key (兼容重旱与涝渍)
            risk_vals = [float(r["risk_score"]) for r in group_records if r.get("risk_score") is not None]
            avg_risk = round(sum(risk_vals) / len(risk_vals), 2) if risk_vals else 0.0

            item: dict[str, Any] = {
                "name": name,
                "record_count": len(group_records),
                "avg_water20cm": avg_water,
                "avg_risk_score": avg_risk,
                "alert_count": alert_count,
                "status": dominant_status,
                "status_counts": dict(status_counts),
            }
            if aggregation == "device":
                # Include city/county context for devices
                sample = group_records[0]
                item["city"] = sample.get("city")
                item["county"] = sample.get("county")
            else:
                item["city"] = group_records[0].get("city")

            items.append(item)

        # Sort: highest avg risk_score first; alert_count as tiebreaker
        items.sort(key=lambda x: (-x["avg_risk_score"], -x["alert_count"]))

        top_items = items[:top_n]
        for idx, item in enumerate(top_items, start=1):
            item["rank"] = idx

        return {
            "aggregation": aggregation,
            "top_n": top_n,
            "total_analyzed": len(groups),
            "items": top_items,
        }

    async def _execute_detail(self, args: dict[str, Any], *, entity_confidence: str = "high") -> dict[str, Any]:
        """Return single entity detail with evidence fields."""
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]
        output_mode = args.get("output_mode", "normal")

        records = await self.repository.filter_records_async(
            city=city, county=county, sn=sn,
            start_time=start_time, end_time=end_time,
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
                "alert_records": [],
                "status_summary": {},
                "empty_result_path": empty_path,
            }

        enriched = [_evaluate_and_merge(r) for r in records]
        # Keep latest-record selection deterministic when multiple devices share
        # the same business timestamp.
        enriched.sort(key=lambda r: str(r.get("sn") or ""))
        enriched.sort(key=lambda r: r.get("create_time") or "", reverse=True)
        latest = enriched[0]

        status_summary: dict[str, int] = defaultdict(int)
        for r in enriched:
            status_summary[r.get("soil_status", "unknown")] += 1

        alert_records = [r for r in enriched if r.get("soil_status") in _ALERT_STATUSES]

        entity_type = "device" if sn else "region"
        entity_name = sn or county or city or "未知"

        result: dict[str, Any] = {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "output_mode": output_mode,
            "record_count": len(enriched),
            "time_window": {"start_time": start_time, "end_time": end_time},
            "latest_record": _slim_record(latest),
            "alert_records": _slim_records(alert_records[:5]),
            "status_summary": dict(status_summary),
        }

        if output_mode == "warning_mode" and alert_records:
            result["warning_data"] = _warning_fields(alert_records[0])

        return result

    async def _execute_comparison(
        self, args: dict[str, Any], *, entity_confidence: str = "high"
    ) -> dict[str, Any]:
        """Compare soil moisture across multiple entities side-by-side.

        Each entity is queried independently with the same time window and
        results are sorted by avg_risk_score (highest first). Empty entities
        are kept in the result so the answer can mention them explicitly.
        """
        entity_type = args.get("entity_type", "region")
        entities: list[dict[str, Any]] = list(args.get("entities") or [])
        start_time = args["start_time"]
        end_time = args["end_time"]

        if not entities:
            return {
                "entity_type": entity_type,
                "time_window": {"start_time": start_time, "end_time": end_time},
                "items": [],
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
                start_time=start_time, end_time=end_time, **kwargs,
            )

            if not records:
                empty_path = await self._auto_diagnose_empty(
                    {**kwargs, "start_time": start_time, "end_time": end_time},
                    entity_confidence,
                )
                items.append({
                    "name": canonical_name or raw_name,
                    "entity_type": entity_type,
                    "entity_level": level or entity_type,
                    "parent_city_name": parent_city_name,
                    "record_count": 0,
                    "avg_water20cm": None,
                    "avg_risk_score": 0.0,
                    "alert_count": 0,
                    "status": "no_data",
                    "empty_result_path": empty_path,
                })
                continue

            enriched = [_evaluate_and_merge(r) for r in records]

            water_vals = [float(r["water20cm"]) for r in enriched if r.get("water20cm") is not None]
            avg_water = round(sum(water_vals) / len(water_vals), 2) if water_vals else None

            risk_vals = [float(r["risk_score"]) for r in enriched if r.get("risk_score") is not None]
            avg_risk = round(sum(risk_vals) / len(risk_vals), 2) if risk_vals else 0.0

            status_counts: dict[str, int] = defaultdict(int)
            for r in enriched:
                status_counts[r.get("soil_status", "unknown")] += 1
            alert_count = sum(v for k, v in status_counts.items() if k in _ALERT_STATUSES)
            dominant_status = max(status_counts.items(), key=lambda x: x[1])[0]

            items.append({
                "name": canonical_name or raw_name,
                "entity_type": entity_type,
                "entity_level": level or entity_type,
                "parent_city_name": parent_city_name,
                "record_count": len(enriched),
                "avg_water20cm": avg_water,
                "avg_risk_score": avg_risk,
                "alert_count": alert_count,
                "status": dominant_status,
                "status_counts": dict(status_counts),
            })

        # Rank: highest avg_risk_score first; alert_count is the tiebreaker
        items.sort(key=lambda x: (-(x["avg_risk_score"] or 0.0), -(x["alert_count"] or 0)))
        for idx, item in enumerate(items, start=1):
            item["rank"] = idx

        return {
            "entity_type": entity_type,
            "time_window": {"start_time": start_time, "end_time": end_time},
            "total_entities": len(entities),
            "items": items,
        }

    async def _execute_diagnose(self, args: dict[str, Any]) -> dict[str, Any]:
        """Return structured diagnosis: entity_not_found / no_data_in_window / data_exists."""
        scenario = args.get("scenario", "period_exists")
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]

        if scenario == "region_exists":
            count = await self.repository.region_record_count_async(city=city, county=county)
            entity_type = "region"
            entity_name = county or city or "未知"
            exists = count > 0
            return {
                "scenario": scenario,
                "entity_type": entity_type,
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

        # period_exists
        summary = await self.repository.period_record_summary_async(
            city=city, county=county, sn=sn,
            start_time=start_time, end_time=end_time,
        )
        in_window = summary.get("period_record_count", 0) or 0
        entity_name = sn or county or city or "全域"
        diagnosis = "data_exists" if in_window > 0 else "no_data_in_window"
        return {
            "scenario": scenario,
            "entity_type": "device" if sn else "region",
            "entity_name": entity_name,
            "entity_exists": True,  # we don't check existence here
            "diagnosis": diagnosis,
            "record_count_all_time": None,
            "record_count_in_window": in_window,
            "message": (
                f"时间段 {start_time[:10]} ~ {end_time[:10]} 内"
                f"{'有' if in_window else '没有'} {entity_name} 的数据"
                + (f"，共 {in_window} 条" if in_window else "，可以扩大时间范围或查询其他时段")
            ),
        }

    # ── empty-result diagnosis ────────────────────────────────────────────────

    async def _auto_diagnose_empty(self, args: dict[str, Any], entity_confidence: str) -> str:
        """Return empty_result_path: normalize_failed / entity_not_found / no_data_in_window."""
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

    # ── validation helpers ────────────────────────────────────────────────────

    def _validate_time_params(self, args: dict[str, Any]) -> None:
        for field in ("start_time", "end_time"):
            val = args.get(field)
            if not val:
                raise ToolValidationError(f"Missing required param: {field}")
            try:
                datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ToolValidationError(f"Invalid datetime format for {field}: {val!r}")

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

        if tool_name == "query_soil_summary":
            output_mode = args.get("output_mode")
            if output_mode in ("anomaly_focus",) and day_span > MAX_ANOMALY_DAYS:
                raise ToolValidationError(
                    f"time_span {day_span} days exceeds {MAX_ANOMALY_DAYS} for anomaly query"
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


# ── record helpers ─────────────────────────────────────────────────────────────

def _evaluate_and_merge(record: dict[str, Any]) -> dict[str, Any]:
    """Return record merged with evaluated status fields."""
    return {**record, **_evaluate_record_status(record)}


def _slim_record(r: dict[str, Any]) -> dict[str, Any]:
    """Return a minimal evidence-sufficient subset of a record."""
    return {k: r.get(k) for k in (
        "sn", "city", "county", "create_time",
        "water20cm", "water40cm", "water60cm", "water80cm",
        "t20cm", "t40cm",
        "soil_status", "warning_level", "display_label",
    )}


def _slim_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_slim_record(r) for r in records]


def _warning_fields(r: dict[str, Any]) -> dict[str, Any]:
    """Return fields needed to populate a warning template."""
    from datetime import datetime as _dt
    ct = r.get("create_time") or ""
    try:
        dt = _dt.strptime(ct, "%Y-%m-%d %H:%M:%S")
        year, month, day, hour = dt.year, dt.month, dt.day, dt.hour
    except ValueError:
        year = month = day = hour = None
    return {
        "year": year, "month": month, "day": day, "hour": hour,
        "city": r.get("city"), "county": r.get("county"),
        "sn": r.get("sn"),
        "water20cm": r.get("water20cm"),
        "warning_level": r.get("warning_level"),
        "display_label": r.get("display_label"),
    }


__all__ = ["ToolExecutorService", "ToolValidationError"]

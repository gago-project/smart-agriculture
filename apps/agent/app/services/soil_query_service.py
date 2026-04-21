from __future__ import annotations

"""Query planning and execution service for soil data access.

This layer turns resolved Flow state into one of the fixed SQL templates from
the plans.  It does not generate arbitrary SQL.  The repository remains the
only place that actually talks to MySQL; this service mainly translates intents
into query-plan dictionaries and standardized query-log records.
"""

from typing import Any

from app.repositories.soil_repository import SoilRepository


class SoilQueryService:
    """Build and run fixed query plans against `SoilRepository`."""

    def __init__(self, repository: SoilRepository):
        """Keep repository access in a thin service for easier node testing."""
        self.repository = repository

    async def fetch_latest_business_time_if_needed(self, *, slots: dict[str, Any], intent: str) -> str | None:
        """Fetch latest business time only for relative/latest time windows."""
        del intent
        if slots.get("time_range") in {None, "latest_business_time", "last_7_days", "last_30_days", "last_week", "year_to_date", "last_2_years", "last_3_years", "last_5_years"}:
            return await self.repository.latest_business_time_async()
        return None

    async def fetch_latest_batch_id(self) -> str | None:
        """Fetch latest imported batch id for "这一批" style questions."""
        return await self.repository.latest_batch_id_async()

    def build_query_plan(
        self,
        *,
        intent: str,
        slots: dict[str, Any],
        business_time: dict[str, Any],
        session_id: str,
        turn_id: int,
        request_id: str,
    ) -> dict[str, Any]:
        """Build the standard query-plan contract consumed by query nodes."""
        query_type_map = {
            "soil_recent_summary": ("recent_summary", "SQL-01"),
            "soil_severity_ranking": ("severity_ranking", "SQL-02"),
            "soil_region_query": ("region_detail", "SQL-03"),
            "soil_device_query": ("device_detail", "SQL-03"),
            "soil_anomaly_query": ("anomaly_list", "SQL-04"),
            "soil_warning_generation": ("latest_record", "SQL-05"),
            "soil_metric_explanation": ("latest_record", "SQL-06"),
            "soil_management_advice": ("latest_record", "SQL-06"),
        }
        query_type, sql_template = query_type_map.get(intent, ("recent_summary", "SQL-01"))
        filters = {
            "city_name": slots.get("city_name"),
            "county_name": slots.get("county_name"),
            "town_name": slots.get("town_name"),
            "device_sn": slots.get("device_sn"),
            "batch_id": business_time.get("resolved_batch_id") or slots.get("batch_id"),
        }
        time_range = {
            "mode": business_time.get("resolved_time_range"),
            "start_time": business_time.get("start_time"),
            "end_time": business_time.get("end_time"),
            "time_basis": business_time.get("time_basis"),
        }
        group_by = [slots["aggregation"]] if slots.get("aggregation") else None
        order_by = ["soil_anomaly_score DESC"] if query_type == "severity_ranking" else ["sample_time DESC"]
        # Summary queries intentionally keep all matching records because they
        # need accurate totals/averages.  Other query types can be limited.
        limit_size = None if query_type == "recent_summary" else int(slots.get("top_n") or 20)
        return {
            "query_type": query_type,
            "sql_template": sql_template,
            "filters": filters,
            "group_by": group_by,
            "metrics": ["soil_anomaly_score"] if query_type == "severity_ranking" else None,
            "order_by": order_by,
            "limit_size": limit_size,
            "time_range": time_range,
            "slots": dict(slots),
            "business_time": dict(business_time),
            "audit": {"session_id": session_id, "turn_id": turn_id, "query_id": f"{request_id}:{query_type}"},
        }

    def build_fallback_query_plan(
        self,
        *,
        fallback_scenario: str,
        slots: dict[str, Any],
        business_time: dict[str, Any],
        session_id: str,
        turn_id: int,
        request_id: str,
    ) -> dict[str, Any]:
        """Build SQL-07 fallback plans used to diagnose empty-data scenarios."""
        return {
            "query_type": "fallback",
            "sql_template": "SQL-07",
            "fallback_scenario": fallback_scenario,
            "filters": {
                "city_name": slots.get("city_name"),
                "county_name": slots.get("county_name"),
                "town_name": slots.get("town_name"),
                "device_sn": slots.get("device_sn"),
                "batch_id": business_time.get("resolved_batch_id") or slots.get("batch_id"),
            },
            "time_range": {
                "mode": business_time.get("resolved_time_range"),
                "start_time": business_time.get("start_time"),
                "end_time": business_time.get("end_time"),
                "time_basis": business_time.get("time_basis"),
            },
            "slots": dict(slots),
            "business_time": dict(business_time),
            "audit": {"session_id": session_id, "turn_id": turn_id, "query_id": f"{request_id}:fallback:{fallback_scenario}"},
        }

    async def execute(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        """Execute one fixed query plan and normalize the result shape."""
        query_type = query_plan["query_type"]
        filters = dict(query_plan.get("filters") or {})
        time_range = dict(query_plan.get("time_range") or {})
        if query_type == "fallback":
            return await self._execute_fallback(query_plan)
        records = await self.repository.filter_records_async(
            city_name=filters.get("city_name"),
            county_name=filters.get("county_name"),
            town_name=filters.get("town_name"),
            device_sn=filters.get("device_sn"),
            batch_id=filters.get("batch_id"),
            start_time=time_range.get("start_time"),
            end_time=time_range.get("end_time"),
            limit=query_plan.get("limit_size"),
        )
        if query_type == "recent_summary":
            return {"records": records}
        if query_type == "severity_ranking":
            # Ranking still uses the returned records; ordering semantics are
            # carried in the plan/result metadata for downstream explanation.
            aggregation = query_plan.get("slots", {}).get("aggregation", "county")
            return {"records": records, "aggregation": aggregation, "top_n": int(query_plan.get("slots", {}).get("top_n") or 5)}
        if query_type in {"region_detail", "device_detail", "latest_record", "anomaly_list"}:
            return {"records": records[:20]}
        return {"records": records}

    def build_query_log_entry(self, *, state, query_plan: dict[str, Any], query_result: dict[str, Any]) -> dict[str, Any]:
        """Translate one executed query into the `agent_query_log` row shape."""
        records = query_result.get("records") or []
        row_count = len(records)
        if "period_record_count" in query_result:
            row_count = int(query_result.get("period_record_count") or 0)
        elif "device_record_count" in query_result:
            row_count = int(query_result.get("device_record_count") or 0)
        elif "region_record_count" in query_result:
            row_count = int(query_result.get("region_record_count") or 0)
        preview = records[:2] if records else {key: value for key, value in query_result.items() if key != "records"}
        source_files = sorted({item.get("source_file") for item in records if item.get("source_file")})
        audit = query_plan.get("audit") or {}
        return {
            "query_id": audit.get("query_id"),
            "session_id": state.session_id,
            "turn_id": state.turn_id,
            "query_type": query_plan.get("query_type"),
            "query_plan_json": query_plan,
            "sql_fingerprint": query_plan.get("sql_template"),
            "time_range_json": query_plan.get("time_range") or {},
            "filters_json": query_plan.get("filters") or {},
            "group_by_json": query_plan.get("group_by"),
            "metrics_json": query_plan.get("metrics"),
            "order_by_json": query_plan.get("order_by"),
            "limit_size": query_plan.get("limit_size"),
            "row_count": row_count,
            "result_preview_json": preview,
            "source_files_json": source_files,
            "status": "empty" if row_count == 0 else "success",
        }

    async def _execute_fallback(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        """Execute SQL-07-style existence checks for empty-data explanations."""
        scenario = query_plan.get("fallback_scenario")
        filters = dict(query_plan.get("filters") or {})
        time_range = dict(query_plan.get("time_range") or {})
        if scenario == "region_exists":
            return {
                "region_record_count": await self.repository.region_record_count_async(
                    city_name=filters.get("city_name"),
                    county_name=filters.get("county_name"),
                    town_name=filters.get("town_name"),
                    batch_id=filters.get("batch_id"),
                ),
                "latest_sample_time": await self.repository.latest_business_time_async(),
            }
        if scenario == "device_exists":
            return {
                "device_record_count": await self.repository.device_record_count_async(
                    filters.get("device_sn") or "",
                    batch_id=filters.get("batch_id"),
                ),
                "latest_sample_time": await self.repository.latest_business_time_async(),
            }
        if scenario in {"period_exists", "latest_business_time"}:
            return await self.repository.period_record_summary_async(
                city_name=filters.get("city_name"),
                county_name=filters.get("county_name"),
                town_name=filters.get("town_name"),
                device_sn=filters.get("device_sn"),
                batch_id=filters.get("batch_id"),
                start_time=time_range.get("start_time"),
                end_time=time_range.get("end_time"),
            )
        return {"latest_sample_time": await self.repository.latest_business_time_async()}


__all__ = ["SoilQueryService"]

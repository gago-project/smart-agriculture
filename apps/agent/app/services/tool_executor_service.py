"""Tool executor: maps LLM tool-call decisions to SQL repository calls.

This is the only place where LLM-supplied parameters touch real data.
Validation here prevents oversized queries and injection paths.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.repositories.soil_repository import SoilRepository

MAX_TOP_N = 20
MAX_RANKING_DAYS = 365
MAX_ANOMALY_DAYS = 180

ALLOWED_TOOLS = {
    "get_soil_overview",
    "get_soil_ranking",
    "get_soil_detail",
    "get_soil_anomaly",
    "get_warning_data",
    "get_advice_context",
    "diagnose_empty_result",
}


class ToolValidationError(ValueError):
    """Raised when LLM-supplied tool parameters fail safety validation."""


class ToolExecutorService:
    """Validate and execute a single LLM tool call against SoilRepository."""

    def __init__(self, repository: SoilRepository) -> None:
        self.repository = repository

    async def execute(self, *, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        """Validate params and execute the named tool. Raises ToolValidationError on bad params."""
        if tool_name not in ALLOWED_TOOLS:
            raise ToolValidationError(f"Unknown tool: {tool_name!r}")
        self._validate_time_params(tool_args)
        self._validate_tool_specific(tool_name, tool_args)

        start_time = tool_args["start_time"]
        end_time = tool_args["end_time"]
        city = tool_args.get("city")
        county = tool_args.get("county")
        sn = tool_args.get("sn")

        if tool_name == "get_soil_ranking":
            top_n = int(tool_args.get("top_n") or 5)
            aggregation = tool_args.get("aggregation", "county")
            records = await self.repository.filter_records_async(
                city=city, county=county, sn=sn,
                start_time=start_time, end_time=end_time,
            )
            return {"records": records, "top_n": top_n, "aggregation": aggregation}

        if tool_name == "diagnose_empty_result":
            return await self._execute_diagnose(tool_args)

        records = await self.repository.filter_records_async(
            city=city, county=county, sn=sn,
            start_time=start_time, end_time=end_time,
        )
        return {"records": records}

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

        if tool_name == "get_soil_ranking":
            top_n = int(args.get("top_n") or 5)
            if top_n > MAX_TOP_N:
                raise ToolValidationError(f"top_n {top_n} exceeds maximum {MAX_TOP_N}")
            aggregation = args.get("aggregation", "county")
            if aggregation == "device" and day_span > MAX_RANKING_DAYS:
                raise ToolValidationError(f"time_span {day_span} days exceeds {MAX_RANKING_DAYS} for device ranking")

        if tool_name == "get_soil_anomaly" and day_span > MAX_ANOMALY_DAYS:
            raise ToolValidationError(f"time_span {day_span} days exceeds {MAX_ANOMALY_DAYS} for anomaly query")

    async def _execute_diagnose(self, args: dict[str, Any]) -> dict[str, Any]:
        scenario = args.get("scenario", "period_exists")
        city = args.get("city")
        county = args.get("county")
        sn = args.get("sn")
        start_time = args["start_time"]
        end_time = args["end_time"]

        if scenario == "region_exists":
            count = await self.repository.region_record_count_async(city=city, county=county)
            return {"region_record_count": count}
        if scenario == "device_exists":
            count = await self.repository.device_record_count_async(sn or "")
            return {"device_record_count": count}
        result = await self.repository.period_record_summary_async(
            city=city, county=county, sn=sn,
            start_time=start_time, end_time=end_time,
        )
        return result

    @staticmethod
    def _day_span(start_time: str, end_time: str) -> int:
        start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        return max((end.date() - start.date()).days + 1, 1)


__all__ = ["ToolExecutorService", "ToolValidationError"]

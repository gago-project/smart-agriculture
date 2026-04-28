"""Parameter Resolver: normalizes LLM-supplied tool args before execution.

Sits between LLM output and ToolExecutorService. Responsible for:
  1. Entity standardization (city/county via RegionAlias table)
  2. Time semantic slot expansion (time_expression → start_time/end_time)
  3. Parameter validation and safety hard limits
  4. Confidence scoring (entity_confidence, time_confidence)

Confidence strategy:
  - entity_confidence == low OR time_confidence == low  → return clarify signal, do not query
  - either == medium                                    → proceed with warning in trace
  - all high                                            → proceed normally
"""
from __future__ import annotations

import calendar
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

_SN_PATTERN = re.compile(r"^SNS\d{8}$", re.IGNORECASE)

_VALID_TIME_EXPRESSIONS = {
    "today", "yesterday", "last_3_days", "last_7_days",
    "last_14_days", "last_30_days", "last_week", "this_month", "last_month",
}


@dataclass
class ResolvedParams:
    """Result of Parameter Resolver for a single tool call."""

    tool_name: str
    raw_args: dict[str, Any]
    resolved_args: dict[str, Any]
    entity_confidence: str = CONFIDENCE_HIGH
    time_confidence: str = CONFIDENCE_HIGH
    warning_trace: list[str] = field(default_factory=list)
    should_clarify: bool = False
    clarify_message: str = ""

    @property
    def overall_confidence(self) -> str:
        if self.entity_confidence == CONFIDENCE_LOW or self.time_confidence == CONFIDENCE_LOW:
            return CONFIDENCE_LOW
        if self.entity_confidence == CONFIDENCE_MEDIUM or self.time_confidence == CONFIDENCE_MEDIUM:
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_HIGH


def _expand_time_expression(expression: str, latest_business_time: str) -> tuple[str, str]:
    """Expand a semantic time_expression to absolute start_time/end_time strings."""
    try:
        lbt = datetime.strptime(latest_business_time[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        lbt = datetime.now()

    d = lbt.date()

    if expression == "today":
        start = datetime(d.year, d.month, d.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
    elif expression == "yesterday":
        yd = d - timedelta(days=1)
        start = datetime(yd.year, yd.month, yd.day)
        end = datetime(yd.year, yd.month, yd.day, 23, 59, 59)
    elif expression == "last_3_days":
        sd = d - timedelta(days=2)
        start = datetime(sd.year, sd.month, sd.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
    elif expression == "last_7_days":
        sd = d - timedelta(days=6)
        start = datetime(sd.year, sd.month, sd.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
    elif expression == "last_14_days":
        sd = d - timedelta(days=13)
        start = datetime(sd.year, sd.month, sd.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
    elif expression == "last_30_days":
        sd = d - timedelta(days=29)
        start = datetime(sd.year, sd.month, sd.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
    elif expression == "last_week":
        # previous full Mon–Sun
        days_since_monday = d.weekday()  # Mon=0, Sun=6
        last_sunday = d - timedelta(days=days_since_monday + 1)
        last_monday = last_sunday - timedelta(days=6)
        start = datetime(last_monday.year, last_monday.month, last_monday.day)
        end = datetime(last_sunday.year, last_sunday.month, last_sunday.day, 23, 59, 59)
    elif expression == "this_month":
        start = datetime(d.year, d.month, 1)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
    elif expression == "last_month":
        if d.month == 1:
            ym, yy = 12, d.year - 1
        else:
            ym, yy = d.month - 1, d.year
        last_day = calendar.monthrange(yy, ym)[1]
        start = datetime(yy, ym, 1)
        end = datetime(yy, ym, last_day, 23, 59, 59)
    else:
        raise ValueError(f"Unknown time_expression: {expression!r}")

    fmt = "%Y-%m-%d %H:%M:%S"
    return start.strftime(fmt), end.strftime(fmt)


class ParameterResolverService:
    """Normalize and validate LLM-supplied tool parameters before execution."""

    def __init__(self, repository: Any = None) -> None:
        """
        Args:
            repository: SoilRepository instance used to load RegionAlias on first use.
                        If None, entity standardization falls back to pass-through.
        """
        self._repository = repository
        self._alias_index: dict[str, dict[str, str]] | None = None  # alias_name → row

    async def _load_alias_index(self) -> dict[str, dict[str, str]]:
        """Load and cache the RegionAlias table from the repository."""
        if self._alias_index is not None:
            return self._alias_index
        if self._repository is None:
            self._alias_index = {}
            return self._alias_index
        try:
            rows = await self._repository.region_alias_rows_async()
            index: dict[str, dict[str, str]] = {}
            for row in rows:
                key = str(row.get("alias_name", "")).strip()
                if key:
                    index[key] = row
            self._alias_index = index
            logger.info("RegionAlias loaded: %d entries", len(index))
        except Exception as exc:
            logger.warning("RegionAlias load failed, entity normalization disabled: %s", exc)
            self._alias_index = {}
        return self._alias_index

    def _normalize_name(self, name: str | None, alias_index: dict) -> tuple[str | None, str]:
        """Normalize a single region name. Returns (canonical, confidence)."""
        if not name:
            return name, CONFIDENCE_HIGH

        name = name.strip()

        # Exact match in alias table
        if name in alias_index:
            canonical = alias_index[name]["canonical_name"]
            if canonical != name:
                logger.debug("RegionAlias: %r → %r", name, canonical)
            return canonical, CONFIDENCE_HIGH

        # Already looks like a canonical form (ends with 市/县/区/省)
        canonical_suffixes = ("市", "县", "区", "省", "乡", "镇")
        if name.endswith(canonical_suffixes):
            return name, CONFIDENCE_HIGH

        # Partial match: name is a prefix of some alias
        for alias, row in alias_index.items():
            if alias.startswith(name) or name.startswith(alias.rstrip("市县区省")):
                canonical = row["canonical_name"]
                logger.debug("RegionAlias fuzzy: %r → %r (medium confidence)", name, canonical)
                return canonical, CONFIDENCE_MEDIUM

        # No match found
        logger.debug("RegionAlias: no match for %r", name)
        return name, CONFIDENCE_LOW

    async def _resolve_entities(
        self,
        raw_args: dict[str, Any],
        alias_index: dict,
    ) -> tuple[dict[str, Any], str, list[str]]:
        """Standardize city/county/sn. Returns (resolved_entity_args, confidence, warnings)."""
        resolved: dict[str, Any] = {}
        warnings: list[str] = []
        confidences: list[str] = []

        city = raw_args.get("city")
        county = raw_args.get("county")
        sn = raw_args.get("sn")

        if city:
            city_canon, city_conf = self._normalize_name(city, alias_index)
            resolved["city"] = city_canon
            confidences.append(city_conf)
            if city_conf == CONFIDENCE_MEDIUM:
                warnings.append(f"城市名称 '{city}' 近似匹配为 '{city_canon}'，请确认")
            elif city_conf == CONFIDENCE_LOW:
                warnings.append(f"城市名称 '{city}' 在地区库中未找到匹配，查询结果可能为空")

        if county:
            county_canon, county_conf = self._normalize_name(county, alias_index)
            resolved["county"] = county_canon
            confidences.append(county_conf)
            if county_conf == CONFIDENCE_MEDIUM:
                warnings.append(f"县区名称 '{county}' 近似匹配为 '{county_canon}'，请确认")
            elif county_conf == CONFIDENCE_LOW:
                warnings.append(f"县区名称 '{county}' 在地区库中未找到匹配，查询结果可能为空")

        if sn:
            if _SN_PATTERN.match(sn):
                resolved["sn"] = sn.upper()
                confidences.append(CONFIDENCE_HIGH)
            else:
                resolved["sn"] = sn
                confidences.append(CONFIDENCE_MEDIUM)
                warnings.append(f"设备编号 '{sn}' 格式不符合 SNSxxxxxxxx，请核对")

        # Overall entity confidence = worst of all fields
        if CONFIDENCE_LOW in confidences:
            entity_conf = CONFIDENCE_LOW
        elif CONFIDENCE_MEDIUM in confidences:
            entity_conf = CONFIDENCE_MEDIUM
        else:
            entity_conf = CONFIDENCE_HIGH

        return resolved, entity_conf, warnings

    def _resolve_time(
        self,
        raw_args: dict[str, Any],
        latest_business_time: str | None,
    ) -> tuple[dict[str, Any], str, list[str]]:
        """Expand time_expression to start_time/end_time. Returns (time_args, confidence, warnings)."""
        warnings: list[str] = []

        time_expression = raw_args.get("time_expression")

        if not time_expression:
            # No time_expression — check if raw start_time/end_time provided (legacy fallback)
            start_time = raw_args.get("start_time")
            end_time = raw_args.get("end_time")
            if start_time and end_time:
                return {"start_time": start_time, "end_time": end_time}, CONFIDENCE_MEDIUM, [
                    "时间参数未使用 time_expression 枚举，已直接透传，建议使用标准时间枚举"
                ]
            return {}, CONFIDENCE_LOW, ["缺少 time_expression 参数，无法确定查询时间范围"]

        if time_expression not in _VALID_TIME_EXPRESSIONS:
            return {}, CONFIDENCE_LOW, [
                f"time_expression '{time_expression}' 不在支持的枚举列表中"
            ]

        lbt = latest_business_time or ""
        if not lbt or lbt == "暂无":
            # No business time available — still expand using wall clock as fallback
            lbt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            warnings.append("数据库最新时间不可用，已使用当前系统时间展开查询窗口")

        try:
            start_time, end_time = _expand_time_expression(time_expression, lbt)
        except Exception as exc:
            return {}, CONFIDENCE_LOW, [f"时间展开失败: {exc}"]

        return {"start_time": start_time, "end_time": end_time}, CONFIDENCE_HIGH, warnings

    async def resolve(
        self,
        tool_name: str,
        raw_args: dict[str, Any],
        latest_business_time: str | None = None,
    ) -> ResolvedParams:
        """Normalize and validate raw LLM tool args. Returns ResolvedParams with confidence."""
        alias_index = await self._load_alias_index()

        # --- entity resolution ---
        entity_resolved, entity_conf, entity_warnings = await self._resolve_entities(
            raw_args, alias_index
        )

        # --- time resolution ---
        time_resolved, time_conf, time_warnings = self._resolve_time(raw_args, latest_business_time)

        all_warnings = entity_warnings + time_warnings

        # Build resolved_args: start with raw non-entity/time keys, then overlay resolved values
        resolved_args: dict[str, Any] = {
            k: v for k, v in raw_args.items()
            if k not in ("city", "county", "sn", "time_expression", "start_time", "end_time")
        }
        resolved_args.update(entity_resolved)
        resolved_args.update(time_resolved)

        # --- confidence decision ---
        should_clarify = entity_conf == CONFIDENCE_LOW or time_conf == CONFIDENCE_LOW
        clarify_parts: list[str] = []
        if entity_conf == CONFIDENCE_LOW:
            clarify_parts += [w for w in entity_warnings if "未找到" in w or "格式不符" in w]
        if time_conf == CONFIDENCE_LOW:
            clarify_parts += [w for w in time_warnings]
        clarify_message = "；".join(clarify_parts) if clarify_parts else ""

        return ResolvedParams(
            tool_name=tool_name,
            raw_args=raw_args,
            resolved_args=resolved_args,
            entity_confidence=entity_conf,
            time_confidence=time_conf,
            warning_trace=all_warnings,
            should_clarify=should_clarify,
            clarify_message=clarify_message,
        )


__all__ = [
    "ParameterResolverService",
    "ResolvedParams",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_MEDIUM",
    "CONFIDENCE_LOW",
]

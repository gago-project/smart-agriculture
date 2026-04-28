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

_REGION_LEVELS = ("city", "county")
_REGION_SUFFIXES = ("市", "县", "区", "省", "乡", "镇")
_LEVEL_LABELS = {"city": "城市名称", "county": "县区名称", None: "地区名称"}


@dataclass(frozen=True)
class RegionAliasCandidate:
    alias_name: str
    canonical_name: str
    region_level: str
    parent_city_name: str | None = None
    alias_source: str = ""


@dataclass
class RegionResolution:
    raw_name: str
    canonical_name: str | None = None
    level: str | None = None
    parent_city_name: str | None = None
    confidence: str = CONFIDENCE_LOW
    warning: str = ""
    should_clarify: bool = False
    clarify_message: str = ""


@dataclass
class EntityResolutionOutcome:
    resolved_args: dict[str, Any]
    confidence: str
    warnings: list[str] = field(default_factory=list)
    should_clarify: bool = False
    clarify_message: str = ""


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
        self._alias_index: dict[str, list[RegionAliasCandidate]] | None = None
        self._alias_version: str | None = None

    @staticmethod
    def _strip_region_suffixes(name: str) -> str:
        stripped = name.strip()
        while stripped.endswith(_REGION_SUFFIXES):
            stripped = stripped[:-1]
        return stripped

    @staticmethod
    def _is_within_one_edit(left: str, right: str) -> bool:
        if left == right:
            return True
        if abs(len(left) - len(right)) > 1:
            return False

        if len(left) == len(right):
            mismatches = sum(1 for a, b in zip(left, right) if a != b)
            return mismatches <= 1

        shorter, longer = (left, right) if len(left) < len(right) else (right, left)
        i = j = mismatches = 0
        while i < len(shorter) and j < len(longer):
            if shorter[i] == longer[j]:
                i += 1
                j += 1
                continue
            mismatches += 1
            if mismatches > 1:
                return False
            j += 1
        return True

    @staticmethod
    def _is_prefix_match(name: str, alias: str) -> bool:
        alias_base = ParameterResolverService._strip_region_suffixes(alias)
        name_base = ParameterResolverService._strip_region_suffixes(name)
        if not alias_base or not name_base:
            return False
        return alias.startswith(name) or alias_base.startswith(name_base) or name_base.startswith(alias_base)

    @staticmethod
    def _dedupe_candidates(candidates: list[RegionAliasCandidate]) -> list[RegionAliasCandidate]:
        unique: dict[tuple[str, str, str | None], RegionAliasCandidate] = {}
        for candidate in candidates:
            key = (candidate.canonical_name, candidate.region_level, candidate.parent_city_name)
            unique.setdefault(key, candidate)
        return sorted(
            unique.values(),
            key=lambda item: (
                item.region_level,
                item.canonical_name,
                item.parent_city_name or "",
                item.alias_name,
            ),
        )

    @staticmethod
    def _candidate_options(candidates: list[RegionAliasCandidate]) -> str:
        return " / ".join(
            f"{item.canonical_name}({item.region_level}{f', {item.parent_city_name}' if item.parent_city_name else ''})"
            for item in ParameterResolverService._dedupe_candidates(candidates)
        )

    @staticmethod
    def _build_alias_index(rows: list[dict[str, Any]]) -> dict[str, list[RegionAliasCandidate]]:
        index: dict[str, list[RegionAliasCandidate]] = {}
        for row in rows:
            alias_name = str(row.get("alias_name", "")).strip()
            canonical_name = str(row.get("canonical_name", "")).strip()
            level = str(row.get("region_level", "")).strip()
            if not alias_name or not canonical_name or level not in _REGION_LEVELS:
                continue
            candidate = RegionAliasCandidate(
                alias_name=alias_name,
                canonical_name=canonical_name,
                region_level=level,
                parent_city_name=(str(row["parent_city_name"]).strip() if row.get("parent_city_name") else None),
                alias_source=str(row.get("alias_source", "")).strip(),
            )
            index.setdefault(alias_name, []).append(candidate)
        return {
            key: ParameterResolverService._dedupe_candidates(value)
            for key, value in index.items()
        }

    async def _load_alias_index(self) -> dict[str, list[RegionAliasCandidate]]:
        """Load and cache the RegionAlias table from the repository."""
        if self._repository is None:
            self._alias_index = {}
            self._alias_version = None
            return self._alias_index

        version_getter = getattr(self._repository, "region_alias_version_async", None)
        current_version: str | None = None
        if callable(version_getter):
            try:
                current_version = str(await version_getter() or "")
                if self._alias_index is not None and current_version == self._alias_version:
                    return self._alias_index
            except Exception as exc:
                if self._alias_index is not None:
                    logger.warning("RegionAlias version probe failed, reusing cached snapshot: %s", exc)
                    return self._alias_index
                logger.warning("RegionAlias version probe failed, falling back to empty index: %s", exc)
                self._alias_index = {}
                self._alias_version = None
                return self._alias_index
        elif self._alias_index is not None:
            return self._alias_index

        try:
            rows = await self._repository.region_alias_rows_async()
            index = self._build_alias_index(rows)
            self._alias_index = index
            self._alias_version = current_version
            logger.info("RegionAlias loaded: %d aliases", len(index))
        except Exception as exc:
            if self._alias_index is not None:
                logger.warning("RegionAlias reload failed, reusing cached snapshot: %s", exc)
                return self._alias_index
            logger.warning("RegionAlias load failed, entity normalization disabled: %s", exc)
            self._alias_index = {}
            self._alias_version = None
        return self._alias_index

    def _filter_exact_candidates(
        self,
        name: str,
        alias_index: dict[str, list[RegionAliasCandidate]],
        allowed_levels: set[str],
    ) -> list[RegionAliasCandidate]:
        return [
            candidate
            for candidate in alias_index.get(name, [])
            if candidate.region_level in allowed_levels
        ]

    def _find_match_candidates(
        self,
        name: str,
        alias_index: dict[str, list[RegionAliasCandidate]],
        allowed_levels: set[str],
        matcher,
    ) -> list[RegionAliasCandidate]:
        matched: list[RegionAliasCandidate] = []
        for alias_name, candidates in alias_index.items():
            if matcher(name, alias_name):
                matched.extend(
                    candidate
                    for candidate in candidates
                    if candidate.region_level in allowed_levels
                )
        return self._dedupe_candidates(matched)

    def _make_region_resolution(
        self,
        *,
        raw_name: str,
        candidates: list[RegionAliasCandidate],
        confidence: str,
        warning: str = "",
        clarify_message: str = "",
    ) -> RegionResolution | None:
        candidates = self._dedupe_candidates(candidates)
        if not candidates:
            return None
        if len(candidates) > 1:
            return RegionResolution(
                raw_name=raw_name,
                confidence=CONFIDENCE_LOW,
                should_clarify=True,
                clarify_message=clarify_message or (
                    f"地区名称 '{raw_name}' 存在多个候选：{self._candidate_options(candidates)}，请补充更明确的地区信息"
                ),
            )
        candidate = candidates[0]
        return RegionResolution(
            raw_name=raw_name,
            canonical_name=candidate.canonical_name,
            level=candidate.region_level,
            parent_city_name=candidate.parent_city_name,
            confidence=confidence,
            warning=warning,
        )

    def _resolve_region_name(
        self,
        name: str | None,
        alias_index: dict[str, list[RegionAliasCandidate]],
        *,
        expected_level: str | None,
        source_field: str | None,
    ) -> RegionResolution:
        if not name:
            return RegionResolution(raw_name="", confidence=CONFIDENCE_HIGH)
        name = name.strip()
        label = _LEVEL_LABELS.get(source_field, _LEVEL_LABELS[None])

        if expected_level in _REGION_LEVELS:
            allowed_levels = {expected_level}
            cross_levels = set(_REGION_LEVELS) - allowed_levels
        else:
            allowed_levels = set(_REGION_LEVELS)
            cross_levels = set()

        exact = self._make_region_resolution(
            raw_name=name,
            candidates=self._filter_exact_candidates(name, alias_index, allowed_levels),
            confidence=CONFIDENCE_HIGH,
        )
        if exact is not None:
            return exact

        if cross_levels:
            cross_exact = self._make_region_resolution(
                raw_name=name,
                candidates=self._filter_exact_candidates(name, alias_index, cross_levels),
                confidence=CONFIDENCE_MEDIUM,
                warning=(
                    f"{label} '{name}' 识别为 {self._level_name(next(iter(cross_levels)))}，需要自动纠正字段"
                ),
            )
            if cross_exact is not None:
                return cross_exact

        typo = self._make_region_resolution(
            raw_name=name,
            candidates=self._find_match_candidates(name, alias_index, allowed_levels, self._is_within_one_edit),
            confidence=CONFIDENCE_MEDIUM,
            warning=f"{label} '{name}' 近似匹配为候选标准名，请确认",
        )
        if typo is not None:
            return typo

        if cross_levels:
            cross_typo = self._make_region_resolution(
                raw_name=name,
                candidates=self._find_match_candidates(name, alias_index, cross_levels, self._is_within_one_edit),
                confidence=CONFIDENCE_MEDIUM,
                warning=(
                    f"{label} '{name}' 近似匹配为 {self._level_name(next(iter(cross_levels)))}，需要自动纠正字段"
                ),
            )
            if cross_typo is not None:
                return cross_typo

        prefix = self._make_region_resolution(
            raw_name=name,
            candidates=self._find_match_candidates(name, alias_index, allowed_levels, self._is_prefix_match),
            confidence=CONFIDENCE_MEDIUM,
            warning=f"{label} '{name}' 近似匹配为候选标准名，请确认",
        )
        if prefix is not None:
            return prefix

        if cross_levels:
            cross_prefix = self._make_region_resolution(
                raw_name=name,
                candidates=self._find_match_candidates(name, alias_index, cross_levels, self._is_prefix_match),
                confidence=CONFIDENCE_MEDIUM,
                warning=(
                    f"{label} '{name}' 近似匹配为 {self._level_name(next(iter(cross_levels)))}，需要自动纠正字段"
                ),
            )
            if cross_prefix is not None:
                return cross_prefix

        logger.debug("RegionAlias: no match for %r", name)
        return RegionResolution(
            raw_name=name,
            confidence=CONFIDENCE_LOW,
            should_clarify=True,
            clarify_message=f"{label} '{name}' 在地区库中未找到匹配，请确认后重试",
        )

    @staticmethod
    def _level_name(level: str) -> str:
        return "市级地区" if level == "city" else "县区"

    @staticmethod
    def _normalize_name(
        name: str | None,
        alias_index: dict[str, list[RegionAliasCandidate]],
        expected_level: str | None = None,
    ) -> tuple[str | None, str]:
        """Compatibility wrapper used by legacy tests."""
        if not name:
            return name, CONFIDENCE_HIGH
        svc = ParameterResolverService()
        result = svc._resolve_region_name(name, alias_index, expected_level=expected_level, source_field=expected_level)
        if result.canonical_name:
            return result.canonical_name, result.confidence
        return name, result.confidence

    async def _resolve_entities(
        self,
        raw_args: dict[str, Any],
        alias_index: dict[str, list[RegionAliasCandidate]],
    ) -> EntityResolutionOutcome:
        """Standardize city/county/sn (and optional entities list)."""
        resolved: dict[str, Any] = {}
        resolved_regions: dict[str, RegionResolution] = {}
        warnings: list[str] = []
        confidences: list[str] = []
        clarify_parts: list[str] = []

        city = raw_args.get("city")
        county = raw_args.get("county")
        sn = raw_args.get("sn")

        if city:
            city_result = self._resolve_region_name(city, alias_index, expected_level="city", source_field="city")
            ok, conflict = self._apply_region_assignment(
                source_field="city",
                result=city_result,
                resolved=resolved,
                resolved_regions=resolved_regions,
                warnings=warnings,
            )
            confidences.append(city_result.confidence)
            if city_result.should_clarify:
                clarify_parts.append(city_result.clarify_message)
            if not ok and conflict:
                clarify_parts.append(conflict)

        if county:
            county_result = self._resolve_region_name(county, alias_index, expected_level="county", source_field="county")
            ok, conflict = self._apply_region_assignment(
                source_field="county",
                result=county_result,
                resolved=resolved,
                resolved_regions=resolved_regions,
                warnings=warnings,
            )
            confidences.append(county_result.confidence)
            if county_result.should_clarify:
                clarify_parts.append(county_result.clarify_message)
            if not ok and conflict:
                clarify_parts.append(conflict)

        parent_conflict = self._validate_parent_city_consistency(resolved, resolved_regions)
        if parent_conflict:
            clarify_parts.append(parent_conflict)
            confidences.append(CONFIDENCE_LOW)

        if sn:
            if _SN_PATTERN.match(sn):
                resolved["sn"] = sn.upper()
                confidences.append(CONFIDENCE_HIGH)
            else:
                resolved["sn"] = sn
                confidences.append(CONFIDENCE_MEDIUM)
                warnings.append(f"设备编号 '{sn}' 格式不符合 SNSxxxxxxxx，请核对")

        # comparison tool: entities is a list — normalize per-item
        entities = raw_args.get("entities")
        if isinstance(entities, list) and entities:
            entity_type = raw_args.get("entity_type", "region")
            normalized_entities: list[dict[str, Any]] = []
            for entity in entities:
                if not entity or not isinstance(entity, str):
                    continue
                if entity_type == "device":
                    if _SN_PATTERN.match(entity):
                        normalized_entities.append(
                            {
                                "raw_name": entity,
                                "canonical_name": entity.upper(),
                                "level": "device",
                                "parent_city_name": None,
                            }
                        )
                        confidences.append(CONFIDENCE_HIGH)
                    else:
                        normalized_entities.append(
                            {
                                "raw_name": entity,
                                "canonical_name": entity,
                                "level": "device",
                                "parent_city_name": None,
                            }
                        )
                        confidences.append(CONFIDENCE_MEDIUM)
                        warnings.append(f"设备编号 '{entity}' 格式不符合 SNSxxxxxxxx，请核对")
                else:
                    entity_result = self._resolve_region_name(
                        entity,
                        alias_index,
                        expected_level=None,
                        source_field=None,
                    )
                    confidences.append(entity_result.confidence)
                    if entity_result.warning:
                        warnings.append(
                            self._finalize_entity_warning(
                                source_field=None,
                                raw_name=entity,
                                result=entity_result,
                                target_field=entity_result.level or "county",
                            )
                        )
                    if entity_result.should_clarify:
                        clarify_parts.append(entity_result.clarify_message)
                        continue
                    normalized_entities.append(
                        {
                            "raw_name": entity,
                            "canonical_name": entity_result.canonical_name,
                            "level": entity_result.level,
                            "parent_city_name": entity_result.parent_city_name,
                        }
                    )
            resolved["entities"] = normalized_entities
            resolved["entity_type"] = entity_type

        # Overall entity confidence = worst of all fields
        if CONFIDENCE_LOW in confidences:
            entity_conf = CONFIDENCE_LOW
        elif CONFIDENCE_MEDIUM in confidences:
            entity_conf = CONFIDENCE_MEDIUM
        else:
            entity_conf = CONFIDENCE_HIGH

        clarify_parts = [part for part in clarify_parts if part]
        return EntityResolutionOutcome(
            resolved_args=resolved,
            confidence=entity_conf,
            warnings=warnings,
            should_clarify=bool(clarify_parts),
            clarify_message="；".join(dict.fromkeys(clarify_parts)),
        )

    def _apply_region_assignment(
        self,
        *,
        source_field: str,
        result: RegionResolution,
        resolved: dict[str, Any],
        resolved_regions: dict[str, RegionResolution],
        warnings: list[str],
    ) -> tuple[bool, str]:
        if result.warning and result.canonical_name and result.level:
            warnings.append(
                self._finalize_entity_warning(
                    source_field=source_field,
                    raw_name=result.raw_name,
                    result=result,
                    target_field=result.level,
                )
            )
        if result.should_clarify or not result.canonical_name or not result.level:
            return False, ""

        target_field = result.level
        existing = resolved.get(target_field)
        if existing is not None and existing != result.canonical_name:
            return (
                False,
                (
                    f"{_LEVEL_LABELS[source_field]} '{result.raw_name}' 自动纠正后会落到 "
                    f"{target_field}='{result.canonical_name}'，但当前已存在 "
                    f"{target_field}='{existing}'，请明确要查询的地区"
                ),
            )

        resolved[target_field] = result.canonical_name
        resolved_regions[target_field] = result
        return True, ""

    def _finalize_entity_warning(
        self,
        *,
        source_field: str | None,
        raw_name: str,
        result: RegionResolution,
        target_field: str,
    ) -> str:
        label = _LEVEL_LABELS.get(source_field, _LEVEL_LABELS[None])
        if source_field and source_field != target_field:
            return (
                f"{label} '{raw_name}' 识别为 '{result.canonical_name}'，已从 "
                f"{source_field} 自动纠正到 {target_field}"
            )
        return f"{label} '{raw_name}' 近似匹配为 '{result.canonical_name}'，请确认"

    @staticmethod
    def _validate_parent_city_consistency(
        resolved: dict[str, Any],
        resolved_regions: dict[str, RegionResolution],
    ) -> str:
        county_result = resolved_regions.get("county")
        city_name = resolved.get("city")
        if not county_result or not city_name or not county_result.parent_city_name:
            return ""
        if county_result.parent_city_name == city_name:
            return ""
        return (
            f"县区 '{resolved['county']}' 的所属市是 '{county_result.parent_city_name}'，"
            f"与当前 city='{city_name}' 不一致，请确认"
        )

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
        entity_resolution = await self._resolve_entities(
            raw_args, alias_index
        )

        # --- time resolution ---
        time_resolved, time_conf, time_warnings = self._resolve_time(raw_args, latest_business_time)

        all_warnings = entity_resolution.warnings + time_warnings

        # Build resolved_args: start with raw non-entity/time keys, then overlay resolved values
        _MANAGED_KEYS = {
            "city", "county", "sn", "entities", "entity_type",
            "time_expression", "start_time", "end_time",
        }
        resolved_args: dict[str, Any] = {
            k: v for k, v in raw_args.items() if k not in _MANAGED_KEYS
        }
        resolved_args.update(entity_resolution.resolved_args)
        resolved_args.update(time_resolved)

        # --- confidence decision ---
        should_clarify = entity_resolution.should_clarify or time_conf == CONFIDENCE_LOW
        clarify_parts: list[str] = []
        if entity_resolution.should_clarify and entity_resolution.clarify_message:
            clarify_parts.append(entity_resolution.clarify_message)
        if time_conf == CONFIDENCE_LOW:
            clarify_parts += [w for w in time_warnings]
        clarify_message = "；".join(clarify_parts) if clarify_parts else ""

        return ResolvedParams(
            tool_name=tool_name,
            raw_args=raw_args,
            resolved_args=resolved_args,
            entity_confidence=entity_resolution.confidence,
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

from __future__ import annotations

"""Region alias resolution and existence validation.

This module owns two related responsibilities:
1. turn user text or LLM slots into canonical city/county/town slots;
2. validate those resolved slots against MySQL facts before SQL planning.
"""

import re
from typing import Any

from app.repositories.soil_repository import SoilRepository


REGION_LEVEL_PRIORITY = {"town": 3, "county": 2, "city": 1}
REGION_SLOT_KEY = {"city": "city_name", "county": "county_name", "town": "town_name"}
REGION_SUFFIXES = {
    "city": ("市",),
    "county": ("县", "区", "市"),
    "town": ("镇", "乡"),
}


def strip_region_suffix(name: str, region_level: str) -> str:
    """Return a short alias by removing the trailing administrative suffix."""
    normalized = str(name or "").strip()
    for suffix in REGION_SUFFIXES.get(region_level, ()):
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            return normalized[: -len(suffix)]
    return normalized


def build_generated_region_alias_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create canonical and suffix-stripped aliases from soil fact records."""
    mappings: dict[tuple[str, str, str, str | None, str | None], dict[str, Any]] = {}
    for record in records:
        city_name = str(record.get("city_name") or "").strip() or None
        county_name = str(record.get("county_name") or "").strip() or None
        town_name = str(record.get("town_name") or "").strip() or None
        for canonical_name, region_level, parent_city_name, parent_county_name in (
            (city_name, "city", None, None),
            (county_name, "county", city_name, None),
            (town_name, "town", city_name, county_name),
        ):
            if not canonical_name:
                continue
            for alias_name in {canonical_name, strip_region_suffix(canonical_name, region_level)}:
                alias_name = alias_name.strip()
                if len(alias_name) < 2:
                    continue
                key = (alias_name, canonical_name, region_level, parent_city_name, parent_county_name)
                mappings[key] = {
                    "alias_name": alias_name,
                    "canonical_name": canonical_name,
                    "region_level": region_level,
                    "parent_city_name": parent_city_name,
                    "parent_county_name": parent_county_name,
                    "alias_source": "generated_fact",
                }
    return sorted(
        mappings.values(),
        key=lambda item: (
            item["region_level"],
            item["alias_name"],
            item["canonical_name"],
            item.get("parent_city_name") or "",
            item.get("parent_county_name") or "",
        ),
    )


def _levenshtein_distance(left: str, right: str) -> int:
    """Return the edit distance between two short Chinese strings."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current[right_index - 1] + 1
            delete_cost = previous[right_index] + 1
            replace_cost = previous[right_index - 1] + (0 if left_char == right_char else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


class RegionAliasResolver:
    """Resolve user text or slot tokens into canonical region slots."""

    def __init__(self, repository: SoilRepository):
        self.repository = repository

    async def resolve_from_text(self, text: str) -> dict[str, Any]:
        mappings = await self._load_alias_mappings()
        return self._resolve_text(text=text, mappings=mappings)

    async def normalize_slots(self, slots: dict[str, Any]) -> dict[str, Any]:
        mappings = await self._load_alias_mappings()
        normalized = dict(slots)
        for region_level, slot_key in REGION_SLOT_KEY.items():
            current = normalized.get(slot_key)
            if not current:
                continue
            outcome = self._resolve_text(text=str(current), mappings=mappings, preferred_level=region_level)
            if outcome["status"] == "matched":
                normalized.update(outcome["slots"])
            elif outcome["status"] == "ambiguous":
                return {"_region_resolution_status": "ambiguous", "_region_resolution_candidates": outcome["candidates"]}
        return normalized

    async def _load_alias_mappings(self) -> list[dict[str, Any]]:
        mappings = await self.repository.region_alias_rows_async()
        existing = {
            (
                item.get("alias_name"),
                item.get("canonical_name"),
                item.get("region_level"),
                item.get("parent_city_name"),
                item.get("parent_county_name"),
            )
            for item in mappings
        }
        for region_name in await self.repository.known_region_names_async():
            region_name = str(region_name or "").strip()
            if not region_name:
                continue
            region_level = "city" if region_name.endswith("市") else "county" if region_name.endswith(("县", "区")) else "town"
            key = (region_name, region_name, region_level, None, None)
            if key not in existing:
                mappings.append(
                    {
                        "alias_name": region_name,
                        "canonical_name": region_name,
                        "region_level": region_level,
                        "parent_city_name": None,
                        "parent_county_name": None,
                        "alias_source": "canonical",
                    }
                )
        return mappings

    def _resolve_text(self, *, text: str, mappings: list[dict[str, Any]], preferred_level: str | None = None) -> dict[str, Any]:
        compact = str(text or "").replace(" ", "")
        exact_matches = self._collect_exact_matches(compact=compact, mappings=mappings, preferred_level=preferred_level)
        if exact_matches:
            return self._pick_resolution(exact_matches)
        fuzzy_matches = self._collect_fuzzy_matches(compact=compact, mappings=mappings, preferred_level=preferred_level)
        if fuzzy_matches:
            return self._pick_resolution(fuzzy_matches, fuzzy_only=True)
        return {"status": "none", "slots": {}, "candidates": []}

    def _collect_exact_matches(
        self,
        *,
        compact: str,
        mappings: list[dict[str, Any]],
        preferred_level: str | None = None,
    ) -> list[dict[str, Any]]:
        matches: dict[tuple[str, str], dict[str, Any]] = {}
        for mapping in mappings:
            alias_name = str(mapping.get("alias_name") or "").strip()
            if len(alias_name) < 2:
                continue
            if preferred_level and mapping.get("region_level") != preferred_level:
                continue
            if alias_name not in compact:
                continue
            match_start = compact.find(alias_name)
            score = 100 if alias_name == mapping.get("canonical_name") else 95 if mapping.get("alias_source") == "manual" else 90
            key = (str(mapping.get("canonical_name")), str(mapping.get("region_level")))
            current = matches.get(key)
            candidate = {
                **mapping,
                "score": score,
                "matched_text": alias_name,
                "match_start": match_start,
                "match_end": match_start + len(alias_name),
            }
            if current is None or (candidate["score"], len(alias_name)) > (current["score"], len(str(current.get("matched_text") or ""))):
                matches[key] = candidate
        return list(matches.values())

    def _collect_fuzzy_matches(
        self,
        *,
        compact: str,
        mappings: list[dict[str, Any]],
        preferred_level: str | None = None,
    ) -> list[dict[str, Any]]:
        chinese_only = "".join(re.findall(r"[\u4e00-\u9fff]+", compact))
        if len(chinese_only) < 2:
            return []
        fuzzy_segments = self._build_fuzzy_segments(chinese_only)
        matches: dict[tuple[str, str], dict[str, Any]] = {}
        for mapping in mappings:
            alias_name = str(mapping.get("alias_name") or "").strip()
            if preferred_level and mapping.get("region_level") != preferred_level:
                continue
            if len(alias_name) < 2:
                continue
            best_distance = None
            best_window = ""
            for segment in fuzzy_segments:
                if len(alias_name) > len(segment):
                    continue
                for index in range(0, len(segment) - len(alias_name) + 1):
                    window = segment[index : index + len(alias_name)]
                    distance = _levenshtein_distance(alias_name, window)
                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        best_window = window
                        if distance == 0:
                            break
            if best_distance != 1 or best_window == alias_name:
                continue
            key = (str(mapping.get("canonical_name")), str(mapping.get("region_level")))
            matches[key] = {**mapping, "score": 80, "matched_text": best_window}
        return list(matches.values())

    def _build_fuzzy_segments(self, chinese_only: str) -> list[str]:
        marker_match = re.search(
            r"(最近一个月|过去一个月|近一个月|最近7天|近7天|上周|最近|数据|墒情|异常|预警|模板|建议|怎么办|什么意思|怎么处理|趋势|排名|最严重|整体情况|总体情况|现在|当前)",
            chinese_only,
        )
        if marker_match and marker_match.start() >= 2:
            return [chinese_only[: marker_match.start()]]
        return [chinese_only]

    def _pick_resolution(self, candidates: list[dict[str, Any]], *, fuzzy_only: bool = False) -> dict[str, Any]:
        ordered = list(candidates)
        if not ordered:
            return {"status": "none", "slots": {}, "candidates": []}
        ordered.sort(
            key=lambda item: (
                item.get("score", 0),
                REGION_LEVEL_PRIORITY.get(str(item.get("region_level")), 0),
                len(str(item.get("matched_text") or item.get("alias_name") or "")),
            ),
            reverse=True,
        )
        top = ordered[0]
        if fuzzy_only and top.get("score") == 80 and len(ordered) > 1:
            return {"status": "none", "slots": {}, "candidates": []}
        if top.get("score") == 80 and len(ordered) > 1:
            return {"status": "ambiguous", "slots": {}, "candidates": [item["canonical_name"] for item in ordered[:3]]}
        for item in ordered[1:]:
            if item.get("score") == top.get("score") and item.get("canonical_name") != top.get("canonical_name"):
                if self._is_parent_child_pair(top, item) and not self._is_same_match_span(top, item):
                    continue
                return {"status": "ambiguous", "slots": {}, "candidates": [candidate["canonical_name"] for candidate in ordered[:3]]}
        return {"status": "matched", "slots": self._mapping_to_slots(top), "candidates": [top["canonical_name"]], "fuzzy_only": fuzzy_only}

    def _is_parent_child_pair(self, left: dict[str, Any], right: dict[str, Any]) -> bool:
        return bool(
            left.get("canonical_name") == right.get("parent_city_name")
            or right.get("canonical_name") == left.get("parent_city_name")
            or left.get("canonical_name") == right.get("parent_county_name")
            or right.get("canonical_name") == left.get("parent_county_name")
        )

    def _is_same_match_span(self, left: dict[str, Any], right: dict[str, Any]) -> bool:
        return left.get("match_start") == right.get("match_start") and left.get("match_end") == right.get("match_end")

    def _mapping_to_slots(self, mapping: dict[str, Any]) -> dict[str, Any]:
        slots = {}
        region_level = str(mapping.get("region_level") or "")
        slot_key = REGION_SLOT_KEY.get(region_level)
        canonical_name = mapping.get("canonical_name")
        if slot_key and canonical_name:
            slots[slot_key] = canonical_name
        if region_level == "county" and mapping.get("parent_city_name"):
            slots["city_name"] = mapping.get("parent_city_name")
        if region_level == "town":
            if mapping.get("parent_city_name"):
                slots["city_name"] = mapping.get("parent_city_name")
            if mapping.get("parent_county_name"):
                slots["county_name"] = mapping.get("parent_county_name")
        return slots


class RegionResolveService:
    """Validate parsed region/device slots against MySQL facts."""

    def __init__(self, repository: SoilRepository):
        """Repository provides async existence checks."""
        self.repository = repository

    async def resolve(self, *, slots: dict[str, Any], intent: str) -> dict[str, Any]:
        """Return slots plus `region_exists` and `device_exists` booleans."""
        del intent
        resolved = dict(slots)
        resolved["region_exists"] = True
        resolved["device_exists"] = True
        if slots.get("device_sn") and not await self.repository.device_exists_async(slots["device_sn"]):
            resolved["device_exists"] = False
        region_name = slots.get("town_name") or slots.get("county_name") or slots.get("city_name")
        if region_name and not await self.repository.region_exists_async(region_name):
            resolved["region_exists"] = False
        return resolved


__all__ = [
    "RegionAliasResolver",
    "RegionResolveService",
    "build_generated_region_alias_rows",
    "strip_region_suffix",
]

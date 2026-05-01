"""Resolve deterministic query profiles from user messages."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
import re
from typing import Any


DEPTH_TO_WATER_FIELD = {
    "20": "water20cm",
    "40": "water40cm",
    "60": "water60cm",
    "80": "water80cm",
}
DEPTH_TO_TEMP_FIELD = {
    "20": "t20cm",
    "40": "t40cm",
    "60": "t60cm",
    "80": "t80cm",
}
AGGREGATION_LABELS = {
    "avg": "平均值",
    "min": "最小值",
    "max": "最大值",
}
FIELD_ALIASES = {
    "gatewayid": ("gatewayid",),
    "sensorid": ("sensorid",),
    "unitid": ("unitid",),
    "lat": ("纬度", "lat"),
    "lon": ("经度", "lon"),
}
FIELDSTATE_FIELDS = (
    "water20cmfieldstate",
    "water40cmfieldstate",
    "water60cmfieldstate",
    "water80cmfieldstate",
    "t20cmfieldstate",
    "t40cmfieldstate",
    "t60cmfieldstate",
    "t80cmfieldstate",
)
_SN_PATTERN = re.compile(r"SNS\d{8}", re.IGNORECASE)
_TOP_N_PATTERN = re.compile(r"(?:前|top)\s*([0-9]+)", re.IGNORECASE)


@dataclass(frozen=True)
class QueryProfile:
    subject: str = "soil"
    data_focus: str = "all_records"
    answer_mode: str = "summary"
    result_grain: str = "aggregate"
    measure: str | None = None
    projection: list[str] = dc_field(default_factory=list)
    compare_mode: str | None = None
    time_window: dict[str, Any] = dc_field(default_factory=dict)
    slots: dict[str, Any] = dc_field(default_factory=dict)
    follow_up_mode: str = "standalone"
    latest_only: bool = False
    aggregation: str | None = None
    field: str | None = None
    fields: list[str] = dc_field(default_factory=list)
    list_target: str | None = None
    group_by: str | None = None
    top_n: int | None = None


class QueryProfileResolverService:
    """Resolve stable query-profile semantics for deterministic data answers."""

    def resolve(
        self,
        *,
        message: str,
        route_decision: Any,
        current_context: dict[str, Any],
        slots: dict[str, Any] | None = None,
        time_window: dict[str, Any] | None = None,
        follow_up_mode: str = "standalone",
    ) -> QueryProfile:
        text = str(message or "").strip()
        prior_profile = self._prior_profile(current_context)
        route = str(getattr(route_decision, "route", "") or "")
        explicit_data_focus = self._resolve_explicit_data_focus(text)
        data_focus = explicit_data_focus or self._inherit_data_focus(
            route=route,
            follow_up_mode=follow_up_mode,
            prior_profile=prior_profile,
        )
        latest_only = self.is_latest_record_request(text)
        count_measure = self._resolve_count_measure(text, data_focus=data_focus, allow_default=False)
        compare_mode = self._resolve_compare_mode(text)
        compare_metric = self._resolve_compare_metric(text, data_focus=data_focus)
        field_mode, field_name, fields, aggregation = self._resolve_field_request(text)
        group_by = self._resolve_group_by(text, route_decision)
        top_n = self._resolve_top_n(text)

        answer_mode = "summary"
        result_grain = "aggregate"
        measure = None
        list_target = getattr(route_decision, "list_target", None)
        if not list_target and route in {"standalone_list", "follow_up_list"}:
            inherited_list_target = str(prior_profile.get("list_target") or "")
            list_target = inherited_list_target or None

        if route == "latest_record":
            answer_mode = "latest_record"
            result_grain = "entity_detail"
        elif route == "count":
            answer_mode = "count"
            measure = count_measure or self._inherited_measure(
                route=route,
                follow_up_mode=follow_up_mode,
                prior_profile=prior_profile,
            )
            if measure is None:
                measure = self._resolve_count_measure(text, data_focus=data_focus)
            result_grain = self._grain_from_measure(measure)
        elif route == "field":
            answer_mode = "field"
            result_grain = "device_list" if field_mode == "filtered_list" else "entity_detail"
            measure = field_name
        elif route == "compare":
            answer_mode = "compare"
            result_grain = "entity_compare"
            measure = compare_metric or self._inherited_measure(
                route=route,
                follow_up_mode=follow_up_mode,
                prior_profile=prior_profile,
            )
        elif route in {"standalone_list", "follow_up_list"}:
            answer_mode = "list"
            result_grain = "record_list" if list_target == "records" else "device_list"
        elif route in {"standalone_group", "follow_up_group", "follow_up_action_expand"} and getattr(route_decision, "query_shape", None) and getattr(route_decision.query_shape, "action", "") == "group":
            answer_mode = "group"
            result_grain = "region_group"
            measure = self._inherited_measure(
                route=route,
                follow_up_mode=follow_up_mode,
                prior_profile=prior_profile,
            )
            if measure is None:
                measure = "alert_device_count" if data_focus == "warning_only" else None
        elif route in {"explicit_detail", "detail", "follow_up_detail"}:
            answer_mode = "detail"
            result_grain = "entity_detail"
        elif route == "summary":
            answer_mode = "summary"
            result_grain = "aggregate"

        if top_n and answer_mode == "summary":
            answer_mode = "group"
            result_grain = "region_group"
            measure = "alert_device_count" if data_focus == "warning_only" else "device_count"

        if group_by is None and answer_mode == "group":
            inherited_group_by = str(prior_profile.get("group_by") or "")
            group_by = inherited_group_by or None

        if compare_mode is None and route == "compare":
            inherited_compare_mode = str(prior_profile.get("compare_mode") or "")
            compare_mode = inherited_compare_mode or None

        if compare_mode == "time_compare":
            answer_mode = "compare"
            result_grain = "entity_compare"

        return QueryProfile(
            subject="soil",
            data_focus=data_focus,
            answer_mode=answer_mode,
            result_grain=result_grain,
            measure=measure,
            projection=fields,
            compare_mode=compare_mode,
            time_window=dict(time_window or {}),
            slots=dict(slots or {}),
            follow_up_mode=follow_up_mode,
            latest_only=latest_only,
            aggregation=aggregation,
            field=field_name,
            fields=fields,
            list_target=list_target,
            group_by=group_by,
            top_n=top_n,
        )

    @staticmethod
    def _prior_profile(current_context: dict[str, Any]) -> dict[str, Any]:
        query_state = (current_context or {}).get("query_state") or {}
        profile = query_state.get("query_profile") or {}
        return profile if isinstance(profile, dict) else {}

    @staticmethod
    def is_latest_record_request(text: str) -> bool:
        normalized = str(text or "")
        return any(token in normalized for token in ("最新一条", "最新记录", "最新一条记录", "最新数据"))

    @staticmethod
    def is_count_request(text: str) -> bool:
        normalized = str(text or "")
        if "多少" not in normalized and "数量" not in normalized:
            return False
        return any(token in normalized for token in ("点位", "设备", "记录", "地区", "区县", "地方"))

    @staticmethod
    def is_field_request(text: str) -> bool:
        normalized = str(text or "")
        if any(field in normalized for field in FIELDSTATE_FIELDS):
            return True
        if "经纬度" in normalized or "纬度" in normalized or "经度" in normalized:
            return True
        if any(token in normalized for token in ("gatewayid", "sensorid", "unitid")):
            return True
        if any(token in normalized for token in ("厘米含水量", "厘米温度", "cm含水量", "cm温度")):
            return True
        return False

    @staticmethod
    def is_compare_request(text: str) -> bool:
        normalized = str(text or "")
        if "对比" in normalized or "比较" in normalized or "谁更" in normalized:
            return True
        return bool(re.search(r"(最近|近|前)\s*[0-9一二两三四五六七八九十百]+\s*天.*和.*前\s*[0-9一二两三四五六七八九十百]+\s*天", normalized))

    @staticmethod
    def _resolve_explicit_data_focus(text: str) -> str | None:
        normalized = str(text or "")
        if any(token in normalized for token in FIELDSTATE_FIELDS):
            return "all_records"
        if "预警" in normalized or "重点关注" in normalized or "需要关注" in normalized:
            return "warning_only"
        if "异常" in normalized and "fieldstate" not in normalized:
            return "warning_only"
        return None

    @staticmethod
    def _inherit_data_focus(
        *,
        route: str,
        follow_up_mode: str,
        prior_profile: dict[str, Any],
    ) -> str:
        if follow_up_mode != "standalone" or route in {"count", "follow_up_list", "follow_up_group", "follow_up_detail"}:
            inherited = str(prior_profile.get("data_focus") or "")
            if inherited:
                return inherited
        return "all_records"

    @staticmethod
    def _resolve_group_by(text: str, route_decision: Any) -> str | None:
        resolved = str(getattr(route_decision, "group_by", "") or "")
        if resolved:
            return resolved
        if "县" in text or "区" in text:
            return "county"
        if "市" in text:
            return "city"
        if "地区" in text or "地方" in text or "区域" in text:
            return "region"
        return None

    @staticmethod
    def _resolve_top_n(text: str) -> int | None:
        match = _TOP_N_PATTERN.search(str(text or ""))
        if not match:
            if "哪个" in text and any(token in text for token in ("县", "区", "地区", "地方", "点位", "设备")):
                return 1
            return None
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _grain_from_measure(measure: str | None) -> str:
        if measure in {"device_count", "alert_device_count"}:
            return "device_list"
        if measure in {"record_count", "alert_record_count"}:
            return "record_list"
        if measure in {"region_count", "alert_region_count"}:
            return "region_group"
        return "aggregate"

    @staticmethod
    def _resolve_count_measure(text: str, *, data_focus: str, allow_default: bool = True) -> str | None:
        normalized = str(text or "")
        if any(token in normalized for token in ("点位", "设备")):
            return "alert_device_count" if data_focus == "warning_only" else "device_count"
        if any(token in normalized for token in ("记录", "条")):
            return "alert_record_count" if data_focus == "warning_only" else "record_count"
        if any(token in normalized for token in ("地区", "区县", "地方")):
            return "alert_region_count" if data_focus == "warning_only" else "region_count"
        if not allow_default:
            return None
        return "alert_device_count" if data_focus == "warning_only" else "record_count"

    @staticmethod
    def _resolve_compare_mode(text: str) -> str | None:
        normalized = str(text or "")
        if re.search(r"(最近|近)\s*[0-9一二两三四五六七八九十百]+\s*天.*和.*前\s*[0-9一二两三四五六七八九十百]+\s*天", normalized):
            return "time_compare"
        return "entity_compare" if "和" in normalized or QueryProfileResolverService.is_compare_request(normalized) else None

    @staticmethod
    def _resolve_compare_metric(text: str, *, data_focus: str) -> str | None:
        normalized = str(text or "")
        if "预警点位" in normalized:
            return "alert_device_count"
        if "预警记录" in normalized:
            return "alert_record_count"
        if "20" in normalized and ("含水量" in normalized or "water20cm" in normalized):
            return "avg_water20cm"
        if "40" in normalized and ("含水量" in normalized or "water40cm" in normalized):
            return "avg_water40cm"
        if data_focus == "warning_only":
            return "alert_device_count"
        return None

    @staticmethod
    def _inherited_measure(
        *,
        route: str,
        follow_up_mode: str,
        prior_profile: dict[str, Any],
    ) -> str | None:
        if follow_up_mode == "standalone" and route not in {"count", "compare"}:
            return None
        inherited = str(prior_profile.get("measure") or "")
        return inherited or None

    def _resolve_field_request(self, text: str) -> tuple[str | None, str | None, list[str], str | None]:
        normalized = str(text or "")
        if any(field in normalized for field in FIELDSTATE_FIELDS):
            for field in FIELDSTATE_FIELDS:
                if field in normalized:
                    return "filtered_list", field, [field], None

        if "经纬度" in normalized:
            return "latest_projection", None, ["lat", "lon"], None

        metadata_fields = [field for field, aliases in FIELD_ALIASES.items() if any(alias in normalized for alias in aliases)]
        if metadata_fields:
            return "latest_projection", None, metadata_fields, None

        aggregation = None
        if "平均" in normalized or "均值" in normalized:
            aggregation = "avg"
        elif "最大" in normalized or "最高" in normalized:
            aggregation = "max"
        elif "最小" in normalized or "最低" in normalized:
            aggregation = "min"

        fields = self._extract_depth_fields(normalized)
        if fields and aggregation:
            return "aggregate", fields[0], fields[:1], aggregation
        if fields:
            return "latest_projection", None, fields, None
        return None, None, [], None

    @staticmethod
    def _extract_depth_fields(text: str) -> list[str]:
        normalized = str(text or "")
        matches: list[str] = []
        for depth in ("20", "40", "60", "80"):
            if depth in normalized and ("含水量" in normalized or "water" in normalized):
                matches.append(DEPTH_TO_WATER_FIELD[depth])
            if depth in normalized and ("温度" in normalized or re.search(rf"{depth}\s*(?:cm|厘米).*(温度|t)", normalized)):
                field = DEPTH_TO_TEMP_FIELD[depth]
                if field not in matches:
                    matches.append(field)
        return matches


__all__ = ["QueryProfile", "QueryProfileResolverService"]

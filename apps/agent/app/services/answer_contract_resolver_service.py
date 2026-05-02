"""Resolve display focus and must-surface facts for main-agent answers."""

from __future__ import annotations

from typing import Any


_EXPLICIT_FOCUSES = {"warning_mode", "advice_mode", "anomaly_focus"}
_WARNING_LABELS = {"heavy_drought": "重旱", "waterlogging": "涝渍", "device_fault": "设备故障"}
_GENERIC_SCOPE_NAMES = {"全局", "全省", "当前对象"}


class AnswerContractResolver:
    """Central answer-contract resolver for the main `/chat` agent path."""

    def resolve_display_focus(
        self,
        *,
        tool_name: str,
        user_input: str,
        requested_output_mode: str | None,
        derived_summary: dict[str, Any],
    ) -> str:
        requested = str(requested_output_mode or "normal")
        if requested in _EXPLICIT_FOCUSES:
            return requested

        alert_count = int(derived_summary.get("alert_count") or 0)
        if tool_name == "query_soil_detail" and alert_count > 0:
            text = str(user_input or "")
            if any(token in text for token in ("详情", "详细情况", "最近怎么样", "具体怎么回事", "情况怎么样")):
                return "anomaly_focus"
        return "normal"

    def build_must_surface_facts(
        self,
        *,
        tool_name: str,
        display_focus: str,
        entity_name: str,
        entity_resolution_trace: dict[str, Any],
        derived_summary: dict[str, Any],
        representative_records: dict[str, Any],
    ) -> list[str]:
        facts: list[str] = []
        if entity_name and entity_name not in _GENERIC_SCOPE_NAMES:
            facts.append(entity_name)

        confidence_notice = str(entity_resolution_trace.get("confidence_notice") or "")
        if confidence_notice:
            facts.append("置信度")

        if tool_name == "query_soil_summary":
            for item in list(derived_summary.get("attention_regions") or [])[:3]:
                region = str(item.get("region") or "").strip()
                if region:
                    facts.append(region)
            if display_focus in {"warning_mode", "anomaly_focus"}:
                alert_count = derived_summary.get("alert_count")
                if alert_count not in (None, ""):
                    facts.append(str(alert_count))
                warning_label = str(derived_summary.get("dominant_warning_type") or "").strip()
                if warning_label:
                    facts.append(warning_label)
            if display_focus == "warning_mode":
                latest_warning = representative_records.get("latest_warning_record") or {}
                sn = str(latest_warning.get("sn") or "").strip()
                water20 = latest_warning.get("water20cm")
                if sn:
                    facts.append(sn)
                if water20 not in (None, ""):
                    facts.append(self._fmt_number(water20))
            if display_focus == "advice_mode":
                stability = str(derived_summary.get("stability_conclusion") or "").strip()
                if stability:
                    facts.append(stability)

        elif tool_name == "query_soil_ranking":
            items = list(derived_summary.get("severity_items") or [])
            for item in items[: min(10, len(items))]:
                name = str(item.get("name") or "").strip()
                count = item.get("alert_record_count")
                if name:
                    facts.append(name)
                if count not in (None, ""):
                    facts.append(str(count))
                city = str(item.get("city") or "").strip()
                county = str(item.get("county") or "").strip()
                if city or county:
                    facts.append(f"{city}{county}")

        elif tool_name == "query_soil_comparison":
            comparison_items = list(derived_summary.get("comparison_items") or [])
            winner = str(derived_summary.get("winner") or "").strip()
            if winner:
                facts.append(winner)
            for item in comparison_items[:2]:
                name = str(item.get("name") or "").strip()
                count = item.get("alert_record_count")
                if name:
                    facts.append(name)
                if count not in (None, ""):
                    facts.append(str(count))

        elif tool_name == "query_soil_detail":
            if display_focus == "warning_mode":
                latest_warning = representative_records.get("latest_warning_record") or {}
                sn = str(latest_warning.get("sn") or "").strip()
                water20 = latest_warning.get("water20cm")
                if sn:
                    facts.append(sn)
                if water20 not in (None, ""):
                    facts.append(self._fmt_number(water20))
            elif display_focus == "anomaly_focus":
                alert_count = derived_summary.get("alert_count")
                warning_label = str(derived_summary.get("dominant_warning_type") or "").strip()
                representative = representative_records.get("representative_alert_record") or {}
                representative_sn = str(representative.get("sn") or "").strip()
                if alert_count not in (None, ""):
                    facts.append(str(alert_count))
                if warning_label:
                    facts.append(warning_label)
                if representative_sn:
                    facts.append(representative_sn)
            elif display_focus == "advice_mode":
                abnormal_period = derived_summary.get("abnormal_period") or {}
                start_time = str(abnormal_period.get("start_time") or "").strip()
                end_time = str(abnormal_period.get("end_time") or "").strip()
                if start_time:
                    facts.append(start_time[:10])
                if end_time:
                    facts.append(end_time[:10])

        return list(dict.fromkeys(fact for fact in facts if fact))

    @staticmethod
    def warning_label(warning_level: str | None) -> str:
        return _WARNING_LABELS.get(str(warning_level or ""), str(warning_level or ""))

    @staticmethod
    def _fmt_number(value: Any) -> str:
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)


__all__ = ["AnswerContractResolver"]

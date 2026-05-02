"""Deterministic renderer for raw-only soil fact query results."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class BusinessAnswerRenderer:
    """Render stable business answers from raw fact fields and direct aggregates."""

    def render(
        self,
        *,
        tool_name: str,
        answer_evidence_profile: dict[str, Any],
    ) -> str:
        if answer_evidence_profile.get("empty_result_path"):
            return self._render_empty(answer_evidence_profile=answer_evidence_profile)

        if tool_name == "query_soil_summary":
            return self._render_summary(answer_evidence_profile=answer_evidence_profile)
        if tool_name == "query_soil_ranking":
            return self._render_ranking(answer_evidence_profile=answer_evidence_profile)
        if tool_name == "query_soil_comparison":
            return self._render_comparison(answer_evidence_profile=answer_evidence_profile)
        if tool_name == "query_soil_detail":
            return self._render_detail(answer_evidence_profile=answer_evidence_profile)
        return "当前已完成查询，但暂时无法整理为稳定结论，请换一种问法重试。"

    def _render_summary(
        self,
        *,
        answer_evidence_profile: dict[str, Any],
    ) -> str:
        entity_name = str(answer_evidence_profile.get("entity_name") or "全局")
        summary = dict(answer_evidence_profile.get("derived_summary") or {})
        trace = dict(answer_evidence_profile.get("entity_resolution_trace") or {})
        total_records = int(summary.get("total_records") or 0)
        device_count = int(summary.get("device_count") or 0)
        region_count = int(summary.get("region_count") or 0)
        avg_water = self._fmt_float(summary.get("avg_water20cm"))
        latest_time = str(summary.get("latest_create_time") or "暂无")
        prefix = self._compose_prefix(
            entity_name=entity_name,
            trace=trace,
            time_window=answer_evidence_profile.get("time_window") or {},
        )
        window_phrase = self._window_phrase(
            time_window=answer_evidence_profile.get("time_window") or {},
            used_context=bool(trace.get("used_context")),
        )
        text = (
            f"{prefix}{entity_name}{window_phrase}共汇总 {total_records} 条记录，"
            f"涉及 {device_count} 个点位、{region_count} 个地区，"
            f"20 厘米平均含水量约 {avg_water}%，最新记录时间为 {latest_time}。"
        )
        stability = str(summary.get("stability_conclusion") or "").strip()
        if stability:
            text += f" {stability}。"
        alert_count = int(summary.get("alert_count") or 0)
        attention_regions = list(summary.get("attention_regions") or [])
        if alert_count > 0:
            text += f" 当前有 {alert_count} 条预警相关记录。"
            if attention_regions:
                top_regions = "、".join(str(item.get("region") or "") for item in attention_regions[:3] if item.get("region"))
                if top_regions:
                    text += f" 重点关注区域主要是 {top_regions}。"
            if answer_evidence_profile.get("display_focus") in {"warning_mode", "anomaly_focus"}:
                warning_label = str(summary.get("dominant_warning_type") or "").strip()
                if warning_label:
                    text += f" 主要异常类型集中在 {warning_label}。"
        if answer_evidence_profile.get("display_focus") == "advice_mode":
            if alert_count <= 0:
                text += " 建议维持日常巡检和例行监测，持续关注后续最新一期数据。"
            else:
                warning_label = str(summary.get("dominant_warning_type") or "").strip()
                if attention_regions:
                    top_regions = "、".join(str(item.get("region") or "") for item in attention_regions[:2] if item.get("region"))
                    if top_regions:
                        text += f" 建议优先巡检 {top_regions}。"
                if warning_label:
                    text += f" 同时重点留意{warning_label}相关点位的后续变化。"
        if answer_evidence_profile.get("display_focus") == "warning_mode":
            latest_warning = (answer_evidence_profile.get("representative_records") or {}).get("latest_warning_record") or {}
            if latest_warning:
                text += (
                    f" 代表性预警样例为 {latest_warning.get('create_time') or '未知时间'} "
                    f"{latest_warning.get('city') or ''}{latest_warning.get('county') or ''}"
                    f"设备 {latest_warning.get('sn') or '未知设备'} 的 "
                    f"{self._fmt_float(latest_warning.get('water20cm'))}% "
                    f"{latest_warning.get('warning_level_label') or latest_warning.get('warning_level') or ''}记录。"
                )
        return text

    def _render_ranking(
        self,
        *,
        answer_evidence_profile: dict[str, Any],
    ) -> str:
        summary = dict(answer_evidence_profile.get("derived_summary") or {})
        items = list(summary.get("severity_items") or [])
        if not items:
            return self._render_empty(answer_evidence_profile=answer_evidence_profile)
        aggregation = str(summary.get("aggregation") or "county")
        window_phrase = self._window_phrase(
            time_window=answer_evidence_profile.get("time_window") or {},
            used_context=False,
        )
        metric_text = "、".join(
            self._ranking_item_text(item, aggregation=aggregation, count_key="alert_record_count")
            for item in items[: min(len(items), int(summary.get("top_n") or 5))]
            if item.get("name")
        )
        unit = "设备" if aggregation == "device" else "地区"
        return f"{window_phrase}按预警记录数排序的前列{unit}依次为 {metric_text}。"

    def _render_comparison(
        self,
        *,
        answer_evidence_profile: dict[str, Any],
    ) -> str:
        summary = dict(answer_evidence_profile.get("derived_summary") or {})
        items = list(summary.get("comparison_items") or [])
        if len(items) < 2:
            return self._render_empty(answer_evidence_profile=answer_evidence_profile)
        window_phrase = self._window_phrase(
            time_window=answer_evidence_profile.get("time_window") or {},
            used_context=False,
        )
        winner = str(summary.get("winner") or "").strip()
        left = items[0]
        right = items[1]
        if winner:
            return (
                f"{window_phrase}按预警记录数对比，{winner}更严重："
                f"{left.get('name')} {int(left.get('alert_record_count') or 0)} 条，"
                f"{right.get('name')} {int(right.get('alert_record_count') or 0)} 条。"
            )
        return (
            f"{window_phrase}按预警记录数对比如下："
            f"{left.get('name')} {int(left.get('alert_record_count') or 0)} 条，"
            f"{right.get('name')} {int(right.get('alert_record_count') or 0)} 条。"
        )

    def _render_detail(
        self,
        *,
        answer_evidence_profile: dict[str, Any],
    ) -> str:
        entity_name = str(answer_evidence_profile.get("entity_name") or "当前对象")
        summary = dict(answer_evidence_profile.get("derived_summary") or {})
        representative_records = dict(answer_evidence_profile.get("representative_records") or {})
        trace = dict(answer_evidence_profile.get("entity_resolution_trace") or {})
        record_count = int(summary.get("record_count") or 0)
        latest = representative_records.get("latest_record") or {}
        prefix = self._compose_prefix(
            entity_name=entity_name,
            trace=trace,
            time_window=answer_evidence_profile.get("time_window") or {},
        )
        window_phrase = self._window_phrase(
            time_window=answer_evidence_profile.get("time_window") or {},
            used_context=bool(trace.get("used_context")),
        )
        latest_digest = dict(summary.get("latest_record_digest") or {})
        location = str(latest_digest.get("location") or self._full_region_context(latest))
        latest_sn = latest.get("sn")
        latest_time = latest_digest.get("latest_time") or latest.get("create_time") or summary.get("latest_create_time") or "未知"
        latest_water = self._fmt_float(latest_digest.get("water20cm") or latest.get("water20cm"))
        avg_water = self._fmt_float(summary.get("avg_water20cm"))
        display_focus = str(answer_evidence_profile.get("display_focus") or "normal")

        if display_focus == "warning_mode":
            latest_warning = representative_records.get("latest_warning_record") or {}
            return (
                f"{prefix}{entity_name}{window_phrase}共有 {record_count} 条记录。"
                f" 最新代表性预警样例是 {latest_warning.get('create_time') or '未知时间'} "
                f"{latest_warning.get('city') or ''}{latest_warning.get('county') or ''}"
                f"设备 {latest_warning.get('sn') or '未知设备'} 的 "
                f"{self._fmt_float(latest_warning.get('water20cm'))}% "
                f"{latest_warning.get('warning_level_label') or latest_warning.get('warning_level') or ''}记录。"
            )
        if display_focus == "advice_mode":
            abnormal_period = summary.get("abnormal_period") or {}
            warning_label = str(summary.get("dominant_warning_type") or "").strip()
            historical_recovery_hint = str(summary.get("historical_recovery_hint") or "").strip()
            return (
                f"{prefix}{entity_name}{window_phrase}共有 {record_count} 条记录，"
                f"最新记录时间 {latest_time}，{f'位于 {location}，' if location else ''}"
                f"20 厘米含水量 {latest_water}%，该时间窗平均值约 {avg_water}%。"
                f" {historical_recovery_hint}，但在 {str(abnormal_period.get('start_time') or '')[:10]} 到 "
                f"{str(abnormal_period.get('end_time') or '')[:10]} 期间曾连续出现{warning_label}记录。"
            )
        if display_focus == "anomaly_focus":
            representative = representative_records.get("representative_alert_record") or {}
            warning_label = str(summary.get("dominant_warning_type") or "").strip()
            return (
                f"{prefix}{entity_name}{window_phrase}共有 {record_count} 条记录，其中 "
                f"{int(summary.get('alert_count') or 0)} 条为预警相关记录，主要异常类型是 {warning_label}。"
                f" 代表性异常点位为 {representative.get('sn') or latest_sn or entity_name}，"
                f"最近异常时间 {representative.get('create_time') or latest_time}，"
                f"{f'位于 {location}，' if location else ''}"
                f"20 厘米含水量 {self._fmt_float(representative.get('water20cm') or latest_water)}%。"
            )

        if answer_evidence_profile.get("entity_type") == "device":
            return (
                f"{prefix}设备 {entity_name}{window_phrase}共有 {record_count} 条记录，"
                f"最新记录时间 {latest_time}，位于 {location or entity_name}，"
                f"20 厘米含水量 {latest_water}%，该时间窗平均值约 {avg_water}%。"
            )

        latest_device_text = f"最新点位 {latest_sn}，" if latest_sn else ""
        return (
            f"{prefix}{entity_name}{window_phrase}共有 {record_count} 条记录，"
            f"{latest_device_text}最新记录时间 {latest_time}，"
            f"{f'位于 {location}，' if location else ''}"
            f"20 厘米含水量 {latest_water}%，该时间窗平均值约 {avg_water}%。"
        )

    def _render_empty(self, *, answer_evidence_profile: dict[str, Any]) -> str:
        entity_name = str(answer_evidence_profile.get("entity_name") or "当前对象")
        time_window = answer_evidence_profile.get("time_window") or {}
        window_range = self._absolute_range_text(time_window)
        empty_path = str(answer_evidence_profile.get("empty_result_path") or "")
        if empty_path == "entity_not_found":
            if answer_evidence_profile.get("entity_type") == "device":
                return f"设备 {entity_name} 在系统中未找到匹配记录，请核对设备编号后重试。"
            return f"地区 {entity_name} 在系统中未找到匹配记录，请核对地区名称后重试。"
        if empty_path == "no_data_in_window":
            return f"{entity_name}在 {window_range} 内未查询到土壤墒情数据，建议扩大时间范围后再查。"
        return f"{entity_name}当前没有可用于回答的问题数据，请补充更明确的时间范围后重试。"

    def _compose_prefix(
        self,
        *,
        entity_name: str,
        trace: dict[str, Any],
        time_window: dict[str, Any],
    ) -> str:
        parts: list[str] = []
        if trace.get("context_correction"):
            parts.append(f"好的，已切换到{entity_name}。")
        confidence_notice = str(trace.get("confidence_notice") or "")
        if confidence_notice:
            parts.append(confidence_notice)
        if trace.get("used_context"):
            label = self._relative_window_label(time_window)
            if label:
                parts.append(f"沿用{label}的时间窗。")
        return "".join(parts)

    def _window_phrase(self, *, time_window: dict[str, Any], used_context: bool) -> str:
        start = self._parse_datetime(time_window.get("start_time"))
        end = self._parse_datetime(time_window.get("end_time"))
        if start is None or end is None:
            return ""
        if used_context:
            return f"在 {self._absolute_range_text(time_window)} 这段时间内"
        if start.date() == end.date():
            return f"最新一期（{start.strftime('%Y-%m-%d')}）"
        if start.month == 1 and start.day == 1 and start.year == end.year:
            return f"今年（{self._absolute_range_text(time_window)}）"
        label = self._relative_window_label(time_window)
        if label:
            return f"{label}（{self._absolute_range_text(time_window)}）"
        return f"在 {self._absolute_range_text(time_window)} 这段时间内"

    def _relative_window_label(self, time_window: dict[str, Any]) -> str:
        start = self._parse_datetime(time_window.get("start_time"))
        end = self._parse_datetime(time_window.get("end_time"))
        if start is None or end is None:
            return ""
        if start.date() == end.date():
            return "最新一期"
        day_span = max((end.date() - start.date()).days + 1, 1)
        if day_span <= 31:
            return f"最近 {day_span} 天"
        return ""

    def _absolute_range_text(self, time_window: dict[str, Any]) -> str:
        start = self._parse_datetime(time_window.get("start_time"))
        end = self._parse_datetime(time_window.get("end_time"))
        if start is None or end is None:
            return "当前时间窗"
        if start.date() == end.date():
            return start.strftime("%Y-%m-%d")
        return f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"

    @staticmethod
    def _full_region_context(record: dict[str, Any]) -> str:
        city = str(record.get("city") or "")
        county = str(record.get("county") or "")
        return f"{city}{county}".strip()

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:19] if pattern.endswith("%S") else text[:10], pattern)
            except ValueError:
                continue
        return None

    @staticmethod
    def _fmt_float(value: Any) -> str:
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "暂无"

    @staticmethod
    def _ranking_item_text(item: dict[str, Any], *, aggregation: str, count_key: str) -> str:
        count = int(item.get(count_key) or 0)
        location = f"{item.get('city') or ''}{item.get('county') or ''}".strip()
        if aggregation == "device":
            if location:
                return f"{item.get('name')}（{location}，{count} 条）"
        if aggregation == "county" and location:
            return f"{location}（{count} 条）"
        return f"{item.get('name')}（{count} 条）"


__all__ = ["BusinessAnswerRenderer"]

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
        result: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
    ) -> str:
        if self._is_empty_result(result):
            return self._render_empty(tool_name=tool_name, result=result, resolved_args=resolved_args)

        if tool_name == "query_soil_summary":
            return self._render_summary(
                result=result,
                resolved_args=resolved_args,
                entity_confidence=entity_confidence,
                time_source=time_source,
                used_context=used_context,
                context_correction=context_correction,
            )
        if tool_name == "query_soil_ranking":
            return self._render_ranking(
                result=result,
                resolved_args=resolved_args,
                entity_confidence=entity_confidence,
                time_source=time_source,
                used_context=used_context,
                context_correction=context_correction,
            )
        if tool_name == "query_soil_comparison":
            return self._render_comparison(
                result=result,
                resolved_args=resolved_args,
                entity_confidence=entity_confidence,
                time_source=time_source,
                used_context=used_context,
                context_correction=context_correction,
            )
        if tool_name == "query_soil_detail":
            return self._render_detail(
                result=result,
                resolved_args=resolved_args,
                entity_confidence=entity_confidence,
                time_source=time_source,
                used_context=used_context,
                context_correction=context_correction,
            )
        return "当前已完成查询，但暂时无法整理为稳定结论，请换一种问法重试。"

    def _render_summary(
        self,
        *,
        result: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
    ) -> str:
        entity_name = self._entity_name(result, resolved_args)
        total_records = int(result.get("total_records") or 0)
        device_count = int(result.get("device_count") or 0)
        region_count = int(result.get("region_count") or 0)
        avg_water = self._fmt_float(result.get("avg_water20cm"))
        latest_time = str(result.get("latest_create_time") or "暂无")
        prefix = self._compose_prefix(
            entity_name=entity_name,
            entity_confidence=entity_confidence,
            used_context=used_context,
            context_correction=context_correction,
            time_window=result.get("time_window") or {},
        )
        window_phrase = self._window_phrase(
            time_window=result.get("time_window") or {},
            time_source=time_source,
            used_context=used_context,
        )
        top_regions = list(result.get("top_regions") or [])
        region_text = "、".join(str(item.get("region") or "") for item in top_regions[:3] if item.get("region"))

        text = (
            f"{prefix}{entity_name}{window_phrase}共汇总 {total_records} 条记录，"
            f"涉及 {device_count} 个点位、{region_count} 个地区，"
            f"20 厘米平均含水量约 {avg_water}%，最新记录时间为 {latest_time}。"
        )
        if region_text:
            text += f" 记录较多的地区包括 {region_text}。"
        return text

    def _render_ranking(
        self,
        *,
        result: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
    ) -> str:
        del entity_confidence, used_context, context_correction
        items = list(result.get("items") or [])
        if not items:
            return self._render_empty(tool_name="query_soil_ranking", result=result, resolved_args=resolved_args)
        aggregation = str(result.get("aggregation") or resolved_args.get("aggregation") or "county")
        window_phrase = self._window_phrase(
            time_window=result.get("time_window") or resolved_args,
            time_source=time_source,
            used_context=False,
        )
        metric_text = "、".join(self._ranking_item_text(item, aggregation=aggregation) for item in items[:3] if item.get("name"))
        unit = "设备" if aggregation == "device" else "地区"
        return f"{window_phrase}按原始记录数排序的前列{unit}依次为 {metric_text}。"

    def _render_comparison(
        self,
        *,
        result: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
    ) -> str:
        del entity_confidence, used_context, context_correction
        items = list(result.get("items") or [])
        if len(items) < 2:
            return self._render_empty(tool_name="query_soil_comparison", result=result, resolved_args=resolved_args)
        window_phrase = self._window_phrase(
            time_window=result.get("time_window") or resolved_args,
            time_source=time_source,
            used_context=False,
        )
        fragments = []
        for item in items[:2]:
            fragments.append(
                f"{item.get('name')} {int(item.get('record_count') or 0)} 条记录，"
                f"{int(item.get('device_count') or 0)} 个点位，"
                f"平均 20 厘米含水量 {self._fmt_float(item.get('avg_water20cm'))}%"
            )
        return f"{window_phrase}原始统计对比如下：{'；'.join(fragments)}。"

    def _render_detail(
        self,
        *,
        result: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
    ) -> str:
        entity_name = self._entity_name(result, resolved_args)
        record_count = int(result.get("record_count") or 0)
        latest = result.get("latest_record") or {}
        prefix = self._compose_prefix(
            entity_name=entity_name,
            entity_confidence=entity_confidence,
            used_context=used_context,
            context_correction=context_correction,
            time_window=result.get("time_window") or {},
        )
        window_phrase = self._window_phrase(
            time_window=result.get("time_window") or {},
            time_source=time_source,
            used_context=used_context,
        )
        location = self._full_region_context(latest)
        latest_sn = latest.get("sn")
        latest_time = latest.get("create_time") or result.get("latest_create_time") or "未知"
        latest_water = self._fmt_float(latest.get("water20cm"))
        avg_water = self._fmt_float(result.get("avg_water20cm"))

        if result.get("entity_type") == "device":
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

    def _render_empty(self, *, tool_name: str, result: dict[str, Any], resolved_args: dict[str, Any]) -> str:
        entity_name = self._entity_name(result, resolved_args)
        time_window = result.get("time_window") or resolved_args
        window_range = self._absolute_range_text(time_window)
        empty_path = str(result.get("empty_result_path") or "")
        if empty_path == "entity_not_found":
            if resolved_args.get("sn"):
                return f"设备 {entity_name} 在系统中未找到匹配记录，请核对设备编号后重试。"
            return f"地区 {entity_name} 在系统中未找到匹配记录，请核对地区名称后重试。"
        if empty_path == "no_data_in_window":
            return f"{entity_name}在 {window_range} 内未查询到土壤墒情数据，建议扩大时间范围后再查。"
        if tool_name == "query_soil_comparison":
            return "当前对比对象中没有足够的有效数据，请补充更明确的地区、设备或时间范围后重试。"
        return f"{entity_name}当前没有可用于回答的问题数据，请补充更明确的时间范围后重试。"

    @staticmethod
    def _is_empty_result(result: dict[str, Any]) -> bool:
        if result.get("empty_result_path"):
            return True
        if "total_records" in result:
            return int(result.get("total_records") or 0) == 0
        if "record_count" in result:
            return int(result.get("record_count") or 0) == 0
        if "items" in result:
            return len(result.get("items") or []) == 0
        return False

    @staticmethod
    def _entity_name(result: dict[str, Any], resolved_args: dict[str, Any]) -> str:
        return str(
            result.get("entity_name")
            or resolved_args.get("sn")
            or resolved_args.get("county")
            or resolved_args.get("city")
            or "全省"
        )

    def _compose_prefix(
        self,
        *,
        entity_name: str,
        entity_confidence: str,
        used_context: bool,
        context_correction: bool,
        time_window: dict[str, Any],
    ) -> str:
        parts: list[str] = []
        if context_correction:
            parts.append(f"好的，已切换到{entity_name}。")
        if entity_confidence == "medium":
            parts.append(f"按近似匹配识别为 {entity_name}，置信度中。")
        if used_context:
            label = self._relative_window_label(time_window)
            if label:
                parts.append(f"沿用{label}的时间窗。")
        return "".join(parts)

    def _window_phrase(self, *, time_window: dict[str, Any], time_source: str | None, used_context: bool) -> str:
        del time_source
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
    def _ranking_item_text(item: dict[str, Any], *, aggregation: str) -> str:
        count = int(item.get("record_count") or 0)
        if aggregation == "device":
            location = f"{item.get('city') or ''}{item.get('county') or ''}".strip()
            if location:
                return f"{item.get('name')}（{location}，{count} 条）"
        return f"{item.get('name')}（{count} 条）"


__all__ = ["BusinessAnswerRenderer"]

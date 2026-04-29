"""Deterministic business answer renderer for soil-moisture queries.

The renderer turns structured tool results into stable user-facing text so the
formal acceptance suite no longer depends on free-form LLM generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

_STATUS_LABELS = {
    "not_triggered": "未触发预警",
    "waterlogging": "涝渍",
    "heavy_drought": "重旱",
    "device_fault": "设备故障",
}


class BusinessAnswerRenderer:
    """Render stable business answers from structured tool outputs."""

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
        """Return the deterministic answer text for one completed tool call."""
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
        avg_water = self._fmt_float(result.get("avg_water20cm"))
        alert_count = int(result.get("alert_count") or 0)
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
        output_mode = str(result.get("output_mode") or "normal")

        if output_mode == "warning_mode":
            top_regions = result.get("top_alert_regions") or []
            region_text = "、".join(
                f"{item.get('region')}（{item.get('alert_count')}）"
                for item in top_regions[:4]
                if item.get("region")
            ) or "暂无重点区域"
            sample = (result.get("alert_records") or [None])[0] or {}
            sample_text = ""
            if sample.get("sn"):
                sample_text = (
                    f"代表性预警样例为 {sample.get('create_time')} 的设备 {sample.get('sn')}"
                    f"（{sample.get('city') or ''}{sample.get('county') or ''}，20 厘米含水量 {self._fmt_float(sample.get('water20cm'))}%）。"
                )
            return (
                f"{prefix}从预警视角看，{entity_name}{window_phrase}共汇总 {total_records} 条记录，"
                f"预警相关记录 {alert_count} 条，重点区域依次是 {region_text}。"
                f"{sample_text}".strip()
            )

        if output_mode == "advice_mode":
            advice = (
                "建议继续保持日常巡检和例行监测。"
                if alert_count == 0
                else "建议优先复核异常点位，并结合最新一期数据持续跟踪。"
            )
            return (
                f"{prefix}从建议视角看，{entity_name}{window_phrase}总体平稳，共有 {total_records} 条记录，"
                f"20 厘米平均含水量约 {avg_water}%，alert_count={alert_count}。{advice}"
            )

        if output_mode == "anomaly_focus":
            dominant_alert = self._dominant_alert_status(result.get("status_counts") or {})
            status_text = _STATUS_LABELS.get(dominant_alert, dominant_alert or "异常")
            return (
                f"{prefix}从异常视角看，{entity_name}{window_phrase}需要重点关注。"
                f"该时间窗共汇总 {total_records} 条记录，20 厘米平均含水量约 {avg_water}%，"
                f"预警相关记录 {alert_count} 条，主要异常类型是 {status_text}。"
            )

        if alert_count == 0:
            return (
                f"{prefix}{entity_name}{window_phrase}共汇总 {total_records} 条记录，"
                f"20 厘米平均含水量约 {avg_water}%，alert_count=0，总体平稳。"
            )
        top_regions = result.get("top_alert_regions") or []
        focus_text = "、".join(
            str(item.get("region") or "")
            for item in top_regions[:3]
            if item.get("region")
        )
        return (
            f"{prefix}{entity_name}{window_phrase}共汇总 {total_records} 条记录，"
            f"20 厘米平均含水量约 {avg_water}%，预警相关记录 {alert_count} 条，"
            f"{'重点区域包括 ' + focus_text + '，' if focus_text else ''}当前需要重点关注。"
        )

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
        leader = items[0]
        metric_text = "、".join(self._ranking_item_text(item, aggregation=aggregation) for item in items[:3] if item.get("name"))
        unit = "设备" if aggregation == "device" else "地区"
        return (
            f"{window_phrase}风险排名里，当前最需要优先关注的{unit}是 {leader.get('name')}。"
            f"前列结果依次为 {metric_text}。"
        )

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
        winner = str(result.get("winner") or items[0].get("name") or "首位对象")
        winner_basis = str(result.get("winner_basis") or "alert_count")
        winner_item = next((item for item in items if item.get("name") == winner), items[0])
        runner_up = next((item for item in items if item.get("name") != winner), items[1])
        basis_text = {
            "alert_count": "预警相关记录数",
            "avg_risk_score": "平均风险分",
            "avg_water20cm": "平均 20 厘米含水量",
            "record_count": "记录数量",
        }.get(winner_basis, "综合风险")
        window_phrase = self._window_phrase(
            time_window=result.get("time_window") or resolved_args,
            time_source=time_source,
            used_context=False,
        )
        return (
            f"{window_phrase}横向对比，{winner}比{runner_up.get('name')}更严重。"
            f"{winner}预警相关记录 {int(winner_item.get('alert_count') or 0)} 条，"
            f"{runner_up.get('name')}为 {int(runner_up.get('alert_count') or 0)} 条；"
            f"本轮判断以{basis_text}为主。"
        )

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
        alert_records = list(result.get("alert_records") or [])
        status_summary = result.get("status_summary") or {}
        alert_count = int(
            result.get("alert_count")
            or sum(int(count or 0) for status, count in status_summary.items() if status in {"waterlogging", "heavy_drought", "device_fault"})
        )
        alert_period = result.get("alert_period_summary") or {}
        representative_alert = (
            alert_period.get("representative_record")
            or (alert_records[0] if alert_records else None)
            or {}
        )
        output_mode = str(result.get("output_mode") or "normal")
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
        latest_time = latest.get("create_time") or "未知"
        latest_water = self._fmt_float(latest.get("water20cm"))

        if output_mode == "warning_mode":
            warning = result.get("warning_data") or latest
            warning_location = f"{warning.get('city') or ''}{warning.get('county') or ''}"
            return (
                f"{prefix}从预警视角看，{entity_name}{window_phrase}共有 {record_count} 条记录。"
                f"当前最需要关注的是 {warning.get('sn')}（{warning_location}），"
                f"时间为 {warning.get('create_time')}，20 厘米含水量 {self._fmt_float(warning.get('water20cm'))}%，"
                f"状态为 {_STATUS_LABELS.get(str(warning.get('soil_status') or ''), str(warning.get('soil_status') or '预警'))}。"
            )

        if output_mode == "advice_mode":
            sampled_alert_start = self._date_text((alert_records[-1] or {}).get("create_time")) if alert_records else ""
            sampled_alert_end = self._date_text((alert_records[0] or {}).get("create_time")) if alert_records else ""
            if len(alert_records) > 1 and sampled_alert_start and sampled_alert_end:
                alert_start = sampled_alert_start
                alert_end = sampled_alert_end
            else:
                alert_start = self._date_text(alert_period.get("start_time"))
                alert_end = self._date_text(alert_period.get("end_time"))
            if representative_alert and alert_start and alert_end:
                dominant_alert = self._dominant_alert_status(status_summary)
                status_text = _STATUS_LABELS.get(dominant_alert, dominant_alert or "异常")
                return (
                    f"{prefix}从建议视角看，设备 {entity_name}{window_phrase}共有 {record_count} 条记录。"
                    f"当前最新记录时间 {latest_time}，位于 {location or entity_name}，20 厘米含水量 {latest_water}%。"
                    f"该设备曾在 {alert_start} 到 {alert_end} 期间出现 {status_text} 记录，"
                    f"代表设备仍是 {representative_alert.get('sn') or entity_name}，建议结合那段历史异常持续关注后续波动。"
                )
            return (
                f"{prefix}从建议视角看，设备 {entity_name}{window_phrase}共有 {record_count} 条记录。"
                f"当前最新记录时间 {latest_time}，位于 {location or entity_name}，20 厘米含水量 {latest_water}%。"
                f"{'当前没有异常告警，建议继续日常巡检。' if alert_count == 0 else '建议结合近期异常记录持续跟踪。'}"
            )

        if output_mode == "anomaly_focus":
            dominant_alert = self._dominant_alert_status(status_summary)
            status_text = _STATUS_LABELS.get(dominant_alert, dominant_alert or "异常")
            entity_prefix = "设备" if result.get("entity_type") == "device" else entity_name
            representative_text = (
                f" 代表设备 {representative_alert.get('sn')} 需要优先复核。"
                if representative_alert.get("sn")
                else ""
            )
            if alert_count and alert_count == record_count:
                return (
                    f"{prefix}{entity_prefix} {entity_name}{window_phrase}共有 {record_count} 条记录，全部为{status_text}状态，"
                    f"位于 {location or entity_name}。最新记录时间 {latest_time}，20 厘米含水量 {latest_water}%，建议立即优先关注。"
                )
            return (
                f"{prefix}{entity_name}{window_phrase}共有 {record_count} 条记录，其中预警相关记录 {alert_count} 条，"
                f"主要异常类型是 {status_text}。"
                f"{representative_text}"
                f"最新记录时间 {latest_time}，位置 {location or entity_name}，20 厘米含水量 {latest_water}%。"
            )

        if result.get("entity_type") == "device":
            return (
                f"{prefix}设备 {entity_name}{window_phrase}共有 {record_count} 条记录，"
                f"最新记录时间 {latest_time}，位于 {location or entity_name}，20 厘米含水量 {latest_water}%。"
                f"{' 当前没有异常告警。' if alert_count == 0 else f' 其中预警相关记录 {alert_count} 条。'}"
            )

        latest_device_text = f"最新设备 {latest_sn}，" if latest_sn else ""
        return (
            f"{prefix}{entity_name}{window_phrase}共有 {record_count} 条记录，"
            f"{latest_device_text}最新记录时间 {latest_time}，20 厘米含水量 {latest_water}%。"
            f"{' 当前没有异常告警。' if alert_count == 0 else f' 其中预警相关记录 {alert_count} 条。'}"
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
    def _date_text(value: Any) -> str:
        dt = BusinessAnswerRenderer._parse_datetime(value)
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def _ranking_item_text(item: dict[str, Any], *, aggregation: str) -> str:
        if aggregation == "device":
            location = f"{item.get('city') or ''}{item.get('county') or ''}".strip()
            if location:
                return f"{item.get('name')}（{location}，{int(item.get('alert_count') or 0)}）"
        return f"{item.get('name')}（{int(item.get('alert_count') or 0)}）"

    @staticmethod
    def _dominant_alert_status(status_counts: dict[str, Any]) -> str | None:
        alert_items = [
            (name, int(count or 0))
            for name, count in status_counts.items()
            if name in {"waterlogging", "heavy_drought", "device_fault"}
        ]
        if not alert_items:
            return None
        return max(alert_items, key=lambda item: item[1])[0]


__all__ = ["BusinessAnswerRenderer"]

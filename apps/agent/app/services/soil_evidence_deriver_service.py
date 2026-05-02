"""Derive shared answer-evidence profiles from raw main-agent tool outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.services.answer_contract_resolver_service import AnswerContractResolver
from app.services.warning_predicate_service import WarningPredicateService


_WARNING_LABELS = {"heavy_drought": "重旱", "waterlogging": "涝渍", "device_fault": "设备故障"}


class SoilEvidenceDeriverService:
    """Build the internal answer-evidence profile without polluting raw tool results."""

    def __init__(
        self,
        *,
        repository: Any | None,
        warning_predicate_service: WarningPredicateService | None = None,
        contract_resolver: AnswerContractResolver | None = None,
    ) -> None:
        self.repository = repository
        self.warning_predicate_service = warning_predicate_service or WarningPredicateService()
        self.contract_resolver = contract_resolver or AnswerContractResolver()

    async def derive(
        self,
        *,
        tool_name: str,
        user_input: str,
        raw_result: dict[str, Any],
        raw_args: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
        resolver_warnings: list[str],
    ) -> dict[str, Any]:
        time_window = dict(raw_result.get("time_window") or {
            "start_time": resolved_args.get("start_time"),
            "end_time": resolved_args.get("end_time"),
        })
        entity_name = str(
            raw_result.get("entity_name")
            or resolved_args.get("sn")
            or resolved_args.get("county")
            or resolved_args.get("city")
            or "全局"
        )
        entity_type = str(raw_result.get("entity_type") or ("device" if resolved_args.get("sn") else "region"))
        rule_row = await self._warning_rule_row()
        entity_resolution_trace = self._entity_resolution_trace(
            raw_args=raw_args,
            resolved_args=resolved_args,
            entity_confidence=entity_confidence,
            time_source=time_source,
            used_context=used_context,
            context_correction=context_correction,
            resolver_warnings=resolver_warnings,
        )

        if tool_name == "query_soil_summary":
            derived_summary, representative_records = await self._derive_summary(
                raw_result=raw_result,
                resolved_args=resolved_args,
                rule_row=rule_row,
            )
            severity_basis = None
            raw_volume_basis = None
        elif tool_name == "query_soil_ranking":
            derived_summary, representative_records = await self._derive_ranking(
                raw_result=raw_result,
                resolved_args=resolved_args,
                rule_row=rule_row,
            )
            severity_basis = "alert_record_count"
            raw_volume_basis = "record_count"
        elif tool_name == "query_soil_comparison":
            derived_summary, representative_records = await self._derive_comparison(
                raw_result=raw_result,
                resolved_args=resolved_args,
                rule_row=rule_row,
            )
            severity_basis = "alert_record_count"
            raw_volume_basis = "record_count"
        elif tool_name == "query_soil_detail":
            derived_summary, representative_records = await self._derive_detail(
                raw_result=raw_result,
                resolved_args=resolved_args,
                rule_row=rule_row,
            )
            severity_basis = None
            raw_volume_basis = None
        else:
            derived_summary = {}
            representative_records = {}
            severity_basis = None
            raw_volume_basis = None

        requested_output_mode = str(raw_result.get("output_mode") or resolved_args.get("output_mode") or "normal")
        display_focus = self.contract_resolver.resolve_display_focus(
            tool_name=tool_name,
            user_input=user_input,
            requested_output_mode=requested_output_mode,
            derived_summary=derived_summary,
        )
        must_surface_facts = self.contract_resolver.build_must_surface_facts(
            tool_name=tool_name,
            display_focus=display_focus,
            entity_name=entity_name,
            entity_resolution_trace=entity_resolution_trace,
            derived_summary=derived_summary,
            representative_records=representative_records,
        )

        return {
            "capability": self._capability_for_tool(tool_name),
            "entity_name": entity_name,
            "entity_type": entity_type,
            "display_focus": display_focus,
            "requested_output_mode": requested_output_mode,
            "severity_basis": severity_basis,
            "raw_volume_basis": raw_volume_basis,
            "time_window": time_window,
            "entity_resolution_trace": entity_resolution_trace,
            "must_surface_facts": must_surface_facts,
            "derived_summary": derived_summary,
            "representative_records": representative_records,
            "empty_result_path": raw_result.get("empty_result_path"),
            "output_mode": display_focus,
        }

    async def _derive_summary(
        self,
        *,
        raw_result: dict[str, Any],
        resolved_args: dict[str, Any],
        rule_row: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        records = await self._load_records(resolved_args)
        warning_records = self._warning_records(records, rule_row)
        latest_warning_record = self._latest_warning_record(warning_records)
        representative_alert = latest_warning_record
        attention_regions = self._attention_regions(warning_records)
        dominant_warning_type = self._dominant_warning_type(warning_records)
        derived_summary = {
            "total_records": int(raw_result.get("total_records") or len(records)),
            "device_count": int(raw_result.get("device_count") or self._device_count(records)),
            "region_count": int(raw_result.get("region_count") or self._region_count(records)),
            "avg_water20cm": raw_result.get("avg_water20cm"),
            "latest_create_time": raw_result.get("latest_create_time"),
            "alert_count": len(warning_records),
            "attention_regions": attention_regions,
            "dominant_warning_type": dominant_warning_type,
            "stability_conclusion": self._stability_conclusion(alert_count=len(warning_records)),
        }
        representative_records = {
            "latest_warning_record": latest_warning_record,
            "representative_alert": representative_alert,
        }
        return derived_summary, representative_records

    async def _derive_ranking(
        self,
        *,
        raw_result: dict[str, Any],
        resolved_args: dict[str, Any],
        rule_row: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        records = await self._load_records(resolved_args)
        warning_records = self._warning_records(records, rule_row)
        aggregation = str(raw_result.get("aggregation") or resolved_args.get("aggregation") or "county")
        severity_items = self._group_severity_items(warning_records, aggregation=aggregation)
        top_n = int(raw_result.get("top_n") or resolved_args.get("top_n") or 5)
        return {
            "aggregation": aggregation,
            "top_n": top_n,
            "severity_items": severity_items[:top_n],
            "alert_count": len(warning_records),
        }, {}

    async def _derive_comparison(
        self,
        *,
        raw_result: dict[str, Any],
        resolved_args: dict[str, Any],
        rule_row: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        comparison_items: list[dict[str, Any]] = []
        for entity in list(resolved_args.get("entities") or []):
            filters = {
                "city": entity.get("canonical_name") if entity.get("level") == "city" else None,
                "county": entity.get("canonical_name") if entity.get("level") == "county" else None,
                "sn": entity.get("canonical_name") if entity.get("level") == "device" else None,
                "start_time": resolved_args.get("start_time"),
                "end_time": resolved_args.get("end_time"),
            }
            records = await self._load_records(filters)
            warning_records = self._warning_records(records, rule_row)
            comparison_items.append({
                "name": entity.get("canonical_name"),
                "alert_record_count": len(warning_records),
                "alert_device_count": self._device_count(warning_records),
                "dominant_warning_type": self._dominant_warning_type(warning_records),
                "avg_water20cm": self._avg_water20cm(records),
            })
        comparison_items.sort(key=lambda item: (-int(item.get("alert_record_count") or 0), str(item.get("name") or "")))
        winner = comparison_items[0]["name"] if len(comparison_items) >= 2 and comparison_items[0]["alert_record_count"] != comparison_items[1]["alert_record_count"] else None
        return {
            "comparison_items": comparison_items,
            "winner": winner,
            "alert_count": sum(int(item.get("alert_record_count") or 0) for item in comparison_items),
        }, {}

    async def _derive_detail(
        self,
        *,
        raw_result: dict[str, Any],
        resolved_args: dict[str, Any],
        rule_row: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        records = await self._load_records(resolved_args)
        warning_records = self._warning_records(records, rule_row)
        latest_record = raw_result.get("latest_record") or (records[0] if records else {})
        latest_warning_record = self._latest_warning_record(warning_records)
        representative_alert_record = self._representative_alert_record(warning_records)
        dominant_warning_type = self._dominant_warning_type(warning_records)
        abnormal_period = self._recent_abnormal_period(warning_records)
        latest_is_warning = False
        if latest_record:
            latest_is_warning = any(
                str(record.get("create_time") or "") == str(latest_record.get("create_time") or "")
                and str(record.get("sn") or "") == str(latest_record.get("sn") or "")
                for record in warning_records
            )
        historical_recovery_hint = ""
        if warning_records and latest_record and not latest_is_warning:
            historical_recovery_hint = "当前最新记录已恢复到未触发预警状态"

        derived_summary = {
            "record_count": int(raw_result.get("record_count") or len(records)),
            "device_count": int(raw_result.get("device_count") or self._device_count(records)),
            "region_count": int(raw_result.get("region_count") or self._region_count(records)),
            "avg_water20cm": raw_result.get("avg_water20cm"),
            "latest_create_time": raw_result.get("latest_create_time"),
            "alert_count": len(warning_records),
            "dominant_warning_type": dominant_warning_type,
            "abnormal_period": abnormal_period,
            "historical_recovery_hint": historical_recovery_hint,
            "latest_record_digest": {
                "latest_time": latest_record.get("create_time") or raw_result.get("latest_create_time"),
                "location": f"{latest_record.get('city') or ''}{latest_record.get('county') or ''}".strip(),
                "water20cm": latest_record.get("water20cm"),
            },
        }
        representative_records = {
            "latest_record": latest_record,
            "latest_warning_record": latest_warning_record,
            "representative_alert_record": representative_alert_record,
        }
        return derived_summary, representative_records

    async def _load_records(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        if self.repository is None:
            return []
        loader = getattr(self.repository, "filter_records_async", None)
        if not callable(loader):
            return []
        return await loader(
            city=filters.get("city"),
            county=filters.get("county"),
            sn=filters.get("sn"),
            start_time=filters.get("start_time"),
            end_time=filters.get("end_time"),
            limit=None,
        )

    async def _warning_rule_row(self) -> dict[str, Any] | None:
        if self.repository is None:
            return None
        getter = getattr(self.repository, "warning_rule_row_async", None)
        if callable(getter):
            return await getter()
        return None

    def _warning_records(self, records: list[dict[str, Any]], rule_row: dict[str, Any] | None) -> list[dict[str, Any]]:
        warning_records: list[dict[str, Any]] = []
        for record in records:
            match = self.warning_predicate_service.evaluate(record, rule_row)
            if not match.matched:
                continue
            enriched = dict(record)
            enriched["warning_level"] = match.warning_level
            enriched["warning_level_label"] = self._warning_label(match.warning_level)
            warning_records.append(enriched)
        return warning_records

    def _attention_regions(self, warning_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for record in warning_records:
            city = str(record.get("city") or "").strip()
            county = str(record.get("county") or "").strip()
            key = (city, county)
            bucket = grouped.setdefault(
                key,
                {
                    "region": county or city,
                    "city": city or None,
                    "county": county or None,
                    "alert_record_count": 0,
                    "alert_device_keys": set(),
                    "latest_alert_time": "",
                },
            )
            bucket["alert_record_count"] += 1
            sn = str(record.get("sn") or "").strip()
            if sn:
                bucket["alert_device_keys"].add(sn)
            bucket["latest_alert_time"] = max(str(bucket.get("latest_alert_time") or ""), str(record.get("create_time") or ""))
        rows: list[dict[str, Any]] = []
        for bucket in grouped.values():
            device_keys = bucket.pop("alert_device_keys")
            bucket["alert_device_count"] = len(device_keys)
            rows.append(bucket)
        rows.sort(
            key=lambda item: (
                -int(item.get("alert_record_count") or 0),
                -int(item.get("alert_device_count") or 0),
                str(item.get("latest_alert_time") or ""),
                str(item.get("region") or ""),
            )
        )
        return rows

    def _group_severity_items(self, warning_records: list[dict[str, Any]], *, aggregation: str) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for record in warning_records:
            city = str(record.get("city") or "").strip()
            county = str(record.get("county") or "").strip()
            sn = str(record.get("sn") or "").strip()
            if aggregation == "city":
                key = (city, "", "")
                name = city
                bucket_city = city or None
                bucket_county = None
            elif aggregation == "device":
                key = (sn, city, county)
                name = sn
                bucket_city = city or None
                bucket_county = county or None
            else:
                key = (county or city, city, county)
                name = county or city
                bucket_city = city or None
                bucket_county = county or None
            bucket = grouped.setdefault(
                key,
                {
                    "name": name,
                    "city": bucket_city,
                    "county": bucket_county,
                    "alert_record_count": 0,
                    "alert_device_keys": set(),
                    "latest_alert_time": "",
                },
            )
            bucket["alert_record_count"] += 1
            if sn:
                bucket["alert_device_keys"].add(sn)
            bucket["latest_alert_time"] = max(str(bucket.get("latest_alert_time") or ""), str(record.get("create_time") or ""))
        items: list[dict[str, Any]] = []
        for bucket in grouped.values():
            device_keys = bucket.pop("alert_device_keys")
            bucket["alert_device_count"] = len(device_keys)
            items.append(bucket)
        items.sort(
            key=lambda item: (
                -int(item.get("alert_record_count") or 0),
                -int(item.get("alert_device_count") or 0),
                str(item.get("latest_alert_time") or ""),
                str(item.get("name") or ""),
            )
        )
        return items

    def _representative_alert_record(self, warning_records: list[dict[str, Any]]) -> dict[str, Any]:
        if not warning_records:
            return {}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in warning_records:
            grouped[str(record.get("sn") or "")].append(record)
        best_records = max(
            grouped.values(),
            key=lambda records: (
                len(records),
                max(str(record.get("create_time") or "") for record in records),
                max(self._safe_float(record.get("water20cm")) or 0 for record in records),
            ),
        )
        best_records.sort(key=lambda record: (str(record.get("create_time") or ""), str(record.get("sn") or "")), reverse=True)
        return best_records[0]

    def _latest_warning_record(self, warning_records: list[dict[str, Any]]) -> dict[str, Any]:
        if not warning_records:
            return {}
        ordered = sorted(
            warning_records,
            key=lambda record: (
                str(record.get("create_time") or ""),
                self._safe_float(record.get("water20cm")) or 0,
                str(record.get("sn") or ""),
            ),
            reverse=True,
        )
        return ordered[0]

    def _recent_abnormal_period(self, warning_records: list[dict[str, Any]]) -> dict[str, Any]:
        if not warning_records:
            return {}
        ordered = sorted(warning_records, key=lambda record: str(record.get("create_time") or ""))
        recent_slice = ordered[-5:] if len(ordered) > 5 else ordered
        return {
            "start_time": str(recent_slice[0].get("create_time") or ""),
            "end_time": str(recent_slice[-1].get("create_time") or ""),
        }

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _avg_water20cm(records: list[dict[str, Any]]) -> float | None:
        values = [float(record["water20cm"]) for record in records if record.get("water20cm") is not None]
        return round(sum(values) / len(values), 2) if values else None

    @staticmethod
    def _device_count(records: list[dict[str, Any]]) -> int:
        return len({str(record.get("sn") or "").strip() for record in records if str(record.get("sn") or "").strip()})

    @staticmethod
    def _region_count(records: list[dict[str, Any]]) -> int:
        return len({
            (str(record.get("city") or "").strip(), str(record.get("county") or "").strip())
            for record in records
            if str(record.get("city") or "").strip() or str(record.get("county") or "").strip()
        })

    @staticmethod
    def _warning_label(warning_level: str | None) -> str:
        return _WARNING_LABELS.get(str(warning_level or ""), str(warning_level or ""))

    def _dominant_warning_type(self, warning_records: list[dict[str, Any]]) -> str:
        if not warning_records:
            return ""
        counter = Counter(str(record.get("warning_level") or "") for record in warning_records)
        warning_level, _count = max(counter.items(), key=lambda item: (item[1], item[0]))
        return self._warning_label(warning_level)

    @staticmethod
    def _stability_conclusion(*, alert_count: int) -> str:
        if alert_count <= 0:
            return "总体平稳"
        return "整体仍以未触发预警为主"

    @staticmethod
    def _capability_for_tool(tool_name: str) -> str:
        if tool_name == "query_soil_summary":
            return "summary"
        if tool_name == "query_soil_ranking":
            return "ranking"
        if tool_name == "query_soil_comparison":
            return "compare"
        if tool_name == "query_soil_detail":
            return "detail"
        return tool_name

    @staticmethod
    def _entity_resolution_trace(
        *,
        raw_args: dict[str, Any],
        resolved_args: dict[str, Any],
        entity_confidence: str,
        time_source: str | None,
        used_context: bool,
        context_correction: bool,
        resolver_warnings: list[str],
    ) -> dict[str, Any]:
        resolved_scope = {
            "city": resolved_args.get("city"),
            "county": resolved_args.get("county"),
            "sn": resolved_args.get("sn"),
        }
        raw_scope = {
            "city": raw_args.get("city"),
            "county": raw_args.get("county"),
            "sn": raw_args.get("sn"),
        }
        target_name = str(
            resolved_scope.get("sn")
            or resolved_scope.get("county")
            or resolved_scope.get("city")
            or ""
        )
        confidence_notice = ""
        if entity_confidence == "medium" and target_name:
            confidence_notice = f"按近似匹配识别为 {target_name}，置信度中。"
        return {
            "raw_scope": raw_scope,
            "resolved_scope": resolved_scope,
            "entity_confidence": entity_confidence,
            "time_source": time_source or "",
            "used_context": used_context,
            "context_correction": context_correction,
            "resolver_warnings": list(resolver_warnings or []),
            "confidence_notice": confidence_notice,
        }


__all__ = ["SoilEvidenceDeriverService"]

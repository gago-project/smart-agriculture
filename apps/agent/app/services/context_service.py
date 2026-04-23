"""Conversation context merge and persistence policy.

Only business context is allowed to flow between turns.  The service may
inherit region, device, and time-window hints for clear follow-up questions,
but it never inherits previous factual conclusions, rankings, or forecast-like
outputs.  This prevents multi-turn memory from polluting new data queries.
"""

from __future__ import annotations


from typing import Any


class ContextService:
    """Merge Redis-backed recent business turns into current request slots."""

    def __init__(self, store):
        """Store is usually `SessionContextRepository`, backed by Redis."""
        self.store = store

    async def load_recent_context(self, session_id: str) -> list[dict[str, Any]]:
        """Load the last few business turns for one session."""
        return await self.store.load_recent_context(session_id)

    def merge_slots(
        self,
        *,
        raw_slots: dict[str, Any],
        recent_context: list[dict[str, Any]],
        intent: str,
        boundary_context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Merge raw parser slots with safe-to-inherit conversation context."""
        merged = dict(raw_slots)
        context_used: dict[str, Any] = {}
        if boundary_context:
            context_used.update(
                {
                    "source_turn_id": boundary_context.get("source_turn_id"),
                    "inheritance_mode": boundary_context.get("inheritance_mode"),
                    "boundary_reason": boundary_context.get("boundary_reason"),
                    "inherited_fields": list(boundary_context.get("inherited_fields") or []),
                    "overridden_fields": list(boundary_context.get("overridden_fields") or []),
                }
            )
            entity_context = dict(boundary_context.get("entity_context") or {})
            query_frame = dict(boundary_context.get("query_frame") or {})
            for key in ("city_name", "county_name", "town_name", "device_sn"):
                value = entity_context.get(key)
                if value and not merged.get(key):
                    merged[key] = value
                    context_used[key] = value
            for key in ("metric", "top_n", "render_mode", "audience", "aggregation", "trend"):
                value = query_frame.get(key)
                if value is not None and merged.get(key) is None:
                    merged[key] = value
                    context_used[key] = value
            resolved_window = dict(boundary_context.get("resolved_window") or {})
            if boundary_context.get("inherit_resolved_window") and resolved_window and not merged.get("time_explicit"):
                if resolved_window.get("time_label"):
                    merged["time_range"] = resolved_window["time_label"]
                    context_used["time_range"] = resolved_window["time_label"]
                merged["inherited_start_time"] = resolved_window.get("start_time")
                merged["inherited_end_time"] = resolved_window.get("end_time")
                merged["inherited_time_explicit"] = resolved_window.get("time_explicit")
            return merged, {key: value for key, value in context_used.items() if value not in (None, [], {})}

        latest_context = recent_context[-1] if recent_context else {}
        latest_turn_id = max([item.get("turn_id", 0) for item in recent_context], default=0)
        source_context = latest_context
        advice_intents = {"soil_metric_explanation", "soil_management_advice"}
        if raw_slots.get("follow_up") and intent not in advice_intents:
            # Follow-up data queries require a concrete prior region/device.
            # If the latest useful context is too old or missing, clarification
            # is safer than guessing the user's intended object.
            source_context = self._latest_concrete_context(recent_context)
            if not source_context:
                context_used["needs_clarification"] = True
                context_used["clarification_reason"] = "missing_business_context"
                return merged, context_used
            source_turn_id = int(source_context.get("turn_id") or 0)
            if latest_turn_id and source_turn_id and latest_turn_id - source_turn_id >= 3:
                context_used["needs_clarification"] = True
                context_used["clarification_reason"] = "decayed_business_context"
                context_used["source_turn_id"] = source_turn_id
                context_used["latest_turn_id"] = latest_turn_id
                return merged, context_used

        region = dict(source_context.get("region") or {})
        entity_reference = dict(source_context.get("entity_reference") or {})

        inherit_region = raw_slots.get("follow_up") or intent in {"soil_metric_explanation", "soil_management_advice"}
        if inherit_region:
            # Only identity-like fields are inherited.  Numeric facts and prior
            # answers are intentionally excluded from the stored context shape.
            for key in ("city_name", "county_name", "town_name"):
                value = region.get(key)
                if value and not merged.get(key):
                    merged[key] = value
                    context_used[key] = value
            if entity_reference.get("device_sn") and not merged.get("device_sn"):
                merged["device_sn"] = entity_reference["device_sn"]
                context_used["device_sn"] = entity_reference["device_sn"]

        if raw_slots.get("follow_up") and latest_context.get("time_window") and not merged.get("time_range"):
            merged["time_range"] = latest_context["time_window"]
            context_used["time_range"] = latest_context["time_window"]

        return merged, context_used

    def should_force_clarification(self, context_used: dict[str, Any]) -> bool:
        """Return whether merge detected an unsafe follow-up."""
        return bool(context_used.get("needs_clarification"))

    def should_force_device_detail(self, *, raw_slots: dict[str, Any], merged_slots: dict[str, Any], context_used: dict[str, Any]) -> bool:
        """Promote metric follow-ups on a device into device detail answers."""
        del context_used
        return bool(raw_slots.get("follow_up") and raw_slots.get("metric") and merged_slots.get("device_sn"))

    def _latest_concrete_context(self, recent_context: list[dict[str, Any]]) -> dict[str, Any]:
        """Find the newest context with a concrete region or device reference."""
        for item in reversed(recent_context):
            region = item.get("region") or {}
            entity_reference = item.get("entity_reference") or {}
            if entity_reference.get("device_sn") or any(region.get(key) for key in ("city_name", "county_name", "town_name")):
                return item
        return {}

    def build_turn_context(
        self,
        *,
        intent: str,
        merged_slots: dict[str, Any],
        business_time: dict[str, Any] | None = None,
        previous_base_query_family: str | None = None,
    ) -> dict[str, Any]:
        """Build the minimal context payload saved after verified answers."""
        business_time = business_time or {}
        family = self.query_family_for_intent(intent)
        base_family = family if family not in {"warning", "advice"} else previous_base_query_family or "detail"
        return {
            "domain": "soil_moisture",
            "entity_context": {
                "city_name": merged_slots.get("city_name"),
                "county_name": merged_slots.get("county_name"),
                "town_name": merged_slots.get("town_name"),
                "device_sn": merged_slots.get("device_sn"),
            },
            "query_frame": {
                "query_family": family,
                "intent": intent,
                "metric": merged_slots.get("metric"),
                "top_n": merged_slots.get("top_n"),
                "render_mode": merged_slots.get("render_mode"),
                "audience": merged_slots.get("audience"),
                "aggregation": merged_slots.get("aggregation"),
                "trend": merged_slots.get("trend"),
            },
            "resolved_window": {
                "start_time": business_time.get("start_time") or merged_slots.get("resolved_start_time"),
                "end_time": business_time.get("end_time") or merged_slots.get("resolved_end_time"),
                "time_label": business_time.get("resolved_time_range") or merged_slots.get("time_range"),
                "time_explicit": merged_slots.get("time_explicit"),
            },
            "base_query_family": base_family,
            "region": {
                "city_name": merged_slots.get("city_name"),
                "county_name": merged_slots.get("county_name"),
                "town_name": merged_slots.get("town_name"),
            },
            "time_window": merged_slots.get("time_range"),
            "entity_reference": {
                "device_sn": merged_slots.get("device_sn"),
                "county_name": merged_slots.get("county_name"),
                "city_name": merged_slots.get("city_name"),
                "town_name": merged_slots.get("town_name"),
            },
            "last_intent": intent,
        }

    def should_save_business_context(self, final_state) -> bool:
        """Decide whether a completed turn is safe to save into Redis memory."""
        non_business_input_types = {
            "greeting",
            "capability_question",
            "meaningless_input",
            "ambiguous_low_confidence",
            "out_of_domain",
            "conversation_closing",
        }
        return bool(
            final_state.final_status == "verified_end"
            and final_state.input_type not in non_business_input_types
            and final_state.intent not in {None, "out_of_scope", "clarification_needed"}
            and final_state.answer_type not in {"fallback_answer", "safe_hint_answer", "boundary_answer", "clarification_answer"}
        )

    @staticmethod
    def query_family_for_intent(intent: str) -> str:
        """Map an intent to a reusable query family."""
        return {
            "soil_recent_summary": "summary",
            "soil_severity_ranking": "ranking",
            "soil_region_query": "detail",
            "soil_device_query": "detail",
            "soil_anomaly_query": "anomaly",
            "soil_warning_generation": "warning",
            "soil_metric_explanation": "advice",
            "soil_management_advice": "advice",
        }.get(str(intent), "detail")


__all__ = ["ContextService"]

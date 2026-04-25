"""Rule-based conversation boundary decisions for multi-turn soil questions."""

from __future__ import annotations

from typing import Any


ENTITY_FIELDS = ("city", "county", "sn")
FRAME_FIELDS = ("metric", "top_n", "render_mode", "audience", "aggregation")


class ConversationBoundaryService:
    """Decide whether a turn carries, resets, converts, or clarifies context."""

    DECAY_TURN_GAP = 3

    def decide(self, *, raw_slots: dict[str, Any], intent: str, recent_context: list[dict[str, Any]], turn_id: int | None = None) -> dict[str, Any]:
        """Return a boundary action plus state patch for the current turn."""
        raw_slots = dict(raw_slots or {})
        current_family = self.query_family_for_intent(intent)
        has_entity = self._has_entity(raw_slots)
        has_explicit_time = bool(raw_slots.get("time_explicit"))
        is_follow_up = bool(raw_slots.get("follow_up"))
        pure_ellipsis = is_follow_up and not has_entity and not has_explicit_time and not self._has_frame_signal(raw_slots)
        latest_context = recent_context[-1] if recent_context else {}
        source_context = self._latest_entity_context(recent_context) if pure_ellipsis else self._latest_concrete_context(recent_context)
        object_only = has_entity and not has_explicit_time and not self._has_frame_signal(raw_slots)

        if is_follow_up and not source_context:
            return self._clarify("clarify_missing_context", "missing_business_context")

        if is_follow_up and source_context and self._is_decayed(source_context, latest_context, turn_id) and not has_entity:
            return self._clarify("clarify_decayed_context", "decayed_business_context", source_context=source_context, latest_context=latest_context)

        if source_context and object_only and self._context_family(source_context) == "ranking":
            return self._build_patch_result("convert_frame", "ranking_to_object_detail", source_context, raw_slots, target_family="detail")

        if source_context and (is_follow_up or object_only or self._is_partial_override(raw_slots)):
            if current_family == "detail" and is_follow_up:
                target_family = self._context_family(source_context)
            elif current_family not in {"summary", "detail"}:
                target_family = current_family
            else:
                target_family = self._context_family(source_context)
            if target_family in {"warning", "advice"} and current_family not in {"warning", "advice"}:
                target_family = source_context.get("base_query_family") or "detail"
            return self._build_patch_result("carry_frame", "compatible_follow_up", source_context, raw_slots, target_family=target_family)

        return {
            "next_action": "reset_frame",
            "inheritance_mode": "reset_frame",
            "patch": {
                "boundary_context": {},
                "context_used": {
                    "inheritance_mode": "reset_frame",
                    "boundary_reason": "complete_or_standalone_question",
                    "source_turn_id": None,
                    "inherited_fields": [],
                    "overridden_fields": [],
                },
            },
        }

    def query_family_for_intent(self, intent: str) -> str:
        """Map an intent to a stable query family."""
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

    def intent_for_family(self, family: str, slots: dict[str, Any]) -> str:
        """Return the nearest executable intent for a query family."""
        if family == "anomaly":
            return "soil_anomaly_query"
        if family == "ranking":
            return "soil_severity_ranking"
        if family == "summary":
            return "soil_recent_summary"
        if family == "warning":
            return "soil_warning_generation"
        if family == "advice":
            return "soil_management_advice"
        if slots.get("sn"):
            return "soil_device_query"
        return "soil_region_query"

    def answer_type_for_intent(self, intent: str) -> str:
        """Return answer type for a normalized intent."""
        return {
            "soil_recent_summary": "soil_summary_answer",
            "soil_severity_ranking": "soil_ranking_answer",
            "soil_region_query": "soil_detail_answer",
            "soil_device_query": "soil_detail_answer",
            "soil_anomaly_query": "soil_anomaly_answer",
            "soil_warning_generation": "soil_warning_answer",
            "soil_metric_explanation": "soil_advice_answer",
            "soil_management_advice": "soil_advice_answer",
        }.get(str(intent), "soil_detail_answer")

    def base_query_family(self, *, intent: str, previous_base_family: str | None = None) -> str:
        """Keep warning/advice as overlays on the previous data query family."""
        family = self.query_family_for_intent(intent)
        if family in {"warning", "advice"}:
            return previous_base_family or "detail"
        return family

    def _build_patch_result(
        self,
        action: str,
        reason: str,
        source_context: dict[str, Any],
        raw_slots: dict[str, Any],
        *,
        target_family: str,
    ) -> dict[str, Any]:
        """Build a state patch carrying frame/window metadata forward."""
        entity_context = dict(source_context.get("entity_context") or source_context.get("entity_reference") or {})
        query_frame = dict(source_context.get("query_frame") or {})
        inherited_window = dict(source_context.get("resolved_window") or {})

        inherited_fields: list[str] = []
        overridden_fields: list[str] = []
        for field in ENTITY_FIELDS:
            if raw_slots.get(field):
                if entity_context.get(field) != raw_slots.get(field):
                    overridden_fields.append(field)
                entity_context[field] = raw_slots[field]
            elif entity_context.get(field):
                inherited_fields.append(field)

        for field in FRAME_FIELDS:
            if raw_slots.get(field) is not None:
                if query_frame.get(field) != raw_slots.get(field):
                    overridden_fields.append(field)
                query_frame[field] = raw_slots[field]
            elif query_frame.get(field) is not None and field in {"metric", "top_n", "aggregation"}:
                inherited_fields.append(field)

        if raw_slots.get("time_explicit"):
            inherited_window = {}
            overridden_fields.append("time_range")
        elif inherited_window:
            inherited_fields.append("resolved_window")

        target_intent = self.intent_for_family(target_family, {**entity_context, **raw_slots})
        target_answer_type = self.answer_type_for_intent(target_intent)
        context_used = {
            "inheritance_mode": action,
            "boundary_reason": reason,
            "source_turn_id": source_context.get("turn_id"),
            "inherited_fields": sorted(set(inherited_fields)),
            "overridden_fields": sorted(set(overridden_fields)),
        }
        return {
            "next_action": action,
            "inheritance_mode": action,
            "patch": {
                "intent": target_intent,
                "answer_type": target_answer_type,
                "boundary_context": {
                    "source_turn_id": source_context.get("turn_id"),
                    "entity_context": entity_context,
                    "query_frame": {**query_frame, "query_family": target_family, "intent": target_intent},
                    "resolved_window": inherited_window,
                    "inherit_resolved_window": bool(inherited_window and not raw_slots.get("time_explicit")),
                    "base_query_family": target_family if target_family not in {"warning", "advice"} else source_context.get("base_query_family"),
                },
                "context_used": context_used,
            },
        }

    def _clarify(self, mode: str, reason: str, *, source_context: dict[str, Any] | None = None, latest_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a clarification boundary result."""
        context_used = {
            "inheritance_mode": mode,
            "boundary_reason": reason,
            "source_turn_id": (source_context or {}).get("turn_id"),
            "latest_turn_id": (latest_context or {}).get("turn_id"),
            "inherited_fields": [],
            "overridden_fields": [],
        }
        return {
            "next_action": mode,
            "inheritance_mode": mode,
            "patch": {
                "intent": "clarification_needed",
                "answer_type": "clarification_answer",
                "context_used": context_used,
                "answer_bundle": {
                    "final_answer": "这个追问缺少可继承的地区、设备或查询框架。请补充地区、设备或时间范围，例如：如东县最近怎么样，或 SNS00204333 最近有没有异常。"
                },
            },
        }

    def _latest_concrete_context(self, recent_context: list[dict[str, Any]]) -> dict[str, Any]:
        """Find the newest context with an entity or a reusable query family."""
        for item in reversed(recent_context):
            entity = item.get("entity_context") or item.get("entity_reference") or item.get("region") or {}
            if any(entity.get(field) for field in ENTITY_FIELDS) or item.get("query_frame") or item.get("last_intent"):
                return item
        return {}

    def _latest_entity_context(self, recent_context: list[dict[str, Any]]) -> dict[str, Any]:
        """Find the newest context with a concrete region or device."""
        for item in reversed(recent_context):
            entity = item.get("entity_context") or item.get("entity_reference") or item.get("region") or {}
            if any(entity.get(field) for field in ENTITY_FIELDS):
                return item
        return {}

    def _context_family(self, context: dict[str, Any]) -> str:
        """Extract context family from new or legacy context shapes."""
        query_frame = context.get("query_frame") or {}
        return query_frame.get("query_family") or context.get("base_query_family") or self.query_family_for_intent(context.get("last_intent") or "")

    def _has_entity(self, slots: dict[str, Any]) -> bool:
        """Return whether current turn has a concrete entity."""
        return any(slots.get(field) for field in ENTITY_FIELDS)

    def _has_frame_signal(self, slots: dict[str, Any]) -> bool:
        """Return whether current turn carries non-entity frame fields."""
        return any(slots.get(field) for field in FRAME_FIELDS)

    def _has_business_action(self, slots: dict[str, Any]) -> bool:
        """Return whether the parser produced an explicit action-like slot."""
        return self._has_frame_signal(slots) or bool(slots.get("time_explicit"))

    def _is_partial_override(self, slots: dict[str, Any]) -> bool:
        """Return whether a turn provides only slots that can override context."""
        return bool((self._has_entity(slots) or self._has_frame_signal(slots) or slots.get("time_explicit")) and slots.get("follow_up"))

    def _is_decayed(self, source_context: dict[str, Any], latest_context: dict[str, Any], turn_id: int | None) -> bool:
        """Return whether the concrete context is too far back for pure ellipsis."""
        source_turn_id = int(source_context.get("turn_id") or 0)
        latest_turn_id = int((latest_context or {}).get("turn_id") or turn_id or 0)
        if latest_turn_id and source_turn_id:
            return latest_turn_id - source_turn_id >= self.DECAY_TURN_GAP
        return False


__all__ = ["ConversationBoundaryService"]

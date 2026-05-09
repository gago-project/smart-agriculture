"""Shared turn-interpretation contract for deterministic soil chat turns."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field, replace
from typing import Any

from app.services.follow_up_action_resolver_service import (
    FollowUpActionResolverService,
    FollowUpActionResult,
)
from app.services.follow_up_intent_resolver_service import (
    FollowUpIntentResolverService,
    FollowUpIntentResult,
)
from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService
from app.services.query_profile_resolver_service import QueryProfile, QueryProfileResolverService
from app.services.turn_route_decision_service import TurnRouteDecision, TurnRouteDecisionService


@dataclass(frozen=True)
class TurnInterpretation:
    normalized_text: str
    conversation_state: str
    follow_up_mode: str
    subject_family: str
    answer_intent: str
    entities: dict[str, Any] = dc_field(default_factory=dict)
    time_window: dict[str, Any] = dc_field(default_factory=dict)
    data_focus: str = "all_records"
    compare_mode: str | None = None
    measure: str | None = None
    warning_type: str | None = None
    status_focus: str | None = None
    profile_answer_mode: str = "summary"
    profile_result_grain: str = "aggregate"
    list_target: str | None = None
    group_by: str | None = None
    latest_only: bool = False
    aggregation: str | None = None
    field: str | None = None
    fields: list[str] = dc_field(default_factory=list)
    top_n: int | None = None
    blocked_reason: str | None = None
    route_key: str = "summary"
    route_subject: str = "soil"
    route_action: str = "summary"
    query_grain: str = "none"
    route_mode: str = "standalone"
    route_source: str = "direct"
    reason_codes: tuple[str, ...] = dc_field(default_factory=tuple)
    route_extra: dict[str, Any] = dc_field(default_factory=dict)
    follow_up_result: FollowUpIntentResult | None = None
    action_result: FollowUpActionResult | None = None
    route_decision: TurnRouteDecision | None = None
    query_profile: QueryProfile | None = None


class TurnInterpretationService:
    """Resolve one shared interpretation object before downstream execution."""

    def __init__(
        self,
        *,
        follow_up_intent_resolver: FollowUpIntentResolverService | None = None,
        follow_up_action_resolver: FollowUpActionResolverService | None = None,
        turn_route_decision_service: TurnRouteDecisionService | None = None,
        query_profile_resolver: QueryProfileResolverService | None = None,
        llm_follow_up_resolver: LlmFollowUpResolverService | Any | None = None,
    ) -> None:
        self.follow_up_intent_resolver = follow_up_intent_resolver or FollowUpIntentResolverService()
        self.follow_up_action_resolver = follow_up_action_resolver or FollowUpActionResolverService()
        self.turn_route_decision_service = turn_route_decision_service or TurnRouteDecisionService()
        self.query_profile_resolver = query_profile_resolver or QueryProfileResolverService()
        self.llm_follow_up_resolver = llm_follow_up_resolver

    async def resolve(
        self,
        *,
        text: str,
        current_context: dict[str, Any] | None,
        entities: dict[str, Any] | None,
        time_evidence: Any | None,
        turn_id: int,
    ) -> TurnInterpretation:
        normalized_text = str(text or "").strip()
        context = current_context if isinstance(current_context, dict) else {}
        extracted_entities = self._normalize_entities(entities)
        follow_up_result = await self._resolve_follow_up_intent(
            text=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
            turn_id=turn_id,
        )
        action_result = self.follow_up_action_resolver.resolve(
            text=normalized_text,
            current_context=context,
            turn_id=turn_id,
        )
        legacy_route_decision = self.turn_route_decision_service.decide(
            message=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
            action_result=action_result,
        )

        blocked_reason = self._blocked_reason(follow_up_result)
        follow_up_mode = self._follow_up_mode(
            follow_up_result=follow_up_result,
            action_result=action_result,
            route_decision=legacy_route_decision,
            blocked_reason=blocked_reason,
        )
        legacy_query_profile = self.query_profile_resolver.resolve(
            message=normalized_text,
            route_decision=legacy_route_decision,
            current_context=context,
            slots={},
            time_window=self._time_window_dict(time_evidence),
            follow_up_mode="standalone" if follow_up_mode == "blocked" else follow_up_mode,
        )

        subject_family = self._subject_family(
            route_decision=legacy_route_decision,
            current_context=context,
            query_profile=legacy_query_profile,
            normalized_text=normalized_text,
        )
        answer_intent = self._answer_intent(
            route_decision=legacy_route_decision,
            follow_up_result=follow_up_result,
            current_context=context,
            query_profile=legacy_query_profile,
            normalized_text=normalized_text,
        )
        measure = self._measure(
            query_profile=legacy_query_profile,
            subject_family=subject_family,
            answer_intent=answer_intent,
            normalized_text=normalized_text,
        )
        group_by = self._group_by(
            route_decision=legacy_route_decision,
            follow_up_result=follow_up_result,
            subject_family=subject_family,
            answer_intent=answer_intent,
            normalized_text=normalized_text,
        )

        interpretation = TurnInterpretation(
            normalized_text=normalized_text,
            conversation_state="closed" if context.get("closed") else "open",
            follow_up_mode=follow_up_mode,
            subject_family=subject_family,
            answer_intent=answer_intent,
            entities=extracted_entities,
            time_window=self._time_window_dict(time_evidence),
            data_focus=legacy_query_profile.data_focus,
            compare_mode=legacy_query_profile.compare_mode,
            measure=measure,
            warning_type=legacy_query_profile.warning_type,
            status_focus=legacy_query_profile.status_focus,
            profile_answer_mode=legacy_query_profile.answer_mode,
            profile_result_grain=legacy_query_profile.result_grain,
            list_target=legacy_query_profile.list_target,
            group_by=group_by,
            latest_only=legacy_query_profile.latest_only,
            aggregation=legacy_query_profile.aggregation,
            field=legacy_query_profile.field,
            fields=list(legacy_query_profile.fields),
            top_n=legacy_query_profile.top_n,
            blocked_reason=blocked_reason,
            route_key=legacy_route_decision.route,
            route_subject=legacy_route_decision.query_shape.subject,
            route_action=legacy_route_decision.query_shape.action,
            query_grain=legacy_route_decision.query_shape.grain,
            route_mode=legacy_route_decision.query_shape.mode,
            route_source=legacy_route_decision.route_source,
            reason_codes=legacy_route_decision.reason_codes,
            route_extra=dict(legacy_route_decision.extra or {}),
            follow_up_result=follow_up_result,
            action_result=action_result,
            route_decision=None,
            query_profile=None,
        )
        route_decision = self.turn_route_decision_service.decide(interpretation=interpretation)
        structured_query_profile = self.query_profile_resolver.resolve(
            interpretation=interpretation,
            message="",
            route_decision=route_decision,
            current_context=context,
            slots={},
            time_window=self._time_window_dict(time_evidence),
            follow_up_mode="standalone" if follow_up_mode == "blocked" else follow_up_mode,
        )
        return replace(
            interpretation,
            route_decision=route_decision,
            query_profile=structured_query_profile,
            data_focus=structured_query_profile.data_focus,
            compare_mode=structured_query_profile.compare_mode,
            measure=structured_query_profile.measure,
            warning_type=structured_query_profile.warning_type,
            status_focus=structured_query_profile.status_focus,
            profile_answer_mode=structured_query_profile.answer_mode,
            profile_result_grain=structured_query_profile.result_grain,
            list_target=structured_query_profile.list_target,
            group_by=structured_query_profile.group_by,
            latest_only=structured_query_profile.latest_only,
            aggregation=structured_query_profile.aggregation,
            field=structured_query_profile.field,
            fields=list(structured_query_profile.fields),
            top_n=structured_query_profile.top_n,
        )

    async def _resolve_follow_up_intent(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        entities: dict[str, list[str]],
        time_evidence: Any | None,
        turn_id: int,
    ) -> FollowUpIntentResult:
        result = self.follow_up_intent_resolver.resolve(
            text=text,
            current_context=current_context,
            extracted_entities=entities,
            time_has_signal=bool(getattr(time_evidence, "has_time_signal", False)),
            turn_id=turn_id,
        )
        latest_target = self._latest_target(current_context)
        if result.uncertain and latest_target and self.llm_follow_up_resolver:
            llm_result = await self.llm_follow_up_resolver.resolve(
                text=text,
                context=current_context,
                latest_target=latest_target,
            )
            if llm_result and getattr(llm_result, "confidence", 0.0) >= 0.75:
                result = FollowUpIntentResult(
                    operation=llm_result.operation,
                    confidence=llm_result.confidence,
                    chosen_target=latest_target,
                    new_slots=llm_result.new_slots,
                    inherit_slots=llm_result.inherit_slots,
                    uncertain=False,
                )
        return result

    @staticmethod
    def _normalize_entities(entities: dict[str, Any] | None) -> dict[str, list[str]]:
        source = entities if isinstance(entities, dict) else {}
        normalized: dict[str, Any] = {}
        for key in ("province", "city", "county", "sn"):
            values = source.get(key) or []
            normalized[key] = [str(value) for value in values if value]
        resolved = source.get("resolved") or []
        normalized["resolved"] = [item for item in resolved if isinstance(item, dict)]
        return normalized

    @staticmethod
    def _latest_target(current_context: dict[str, Any]) -> dict[str, Any] | None:
        targets = current_context.get("follow_up_targets") or []
        return targets[0] if targets else None

    @staticmethod
    def _blocked_reason(follow_up_result: FollowUpIntentResult) -> str | None:
        if follow_up_result.operation != "clarify":
            return None
        return follow_up_result.clarify_reason or "clarification"

    @staticmethod
    def _follow_up_mode(
        *,
        follow_up_result: FollowUpIntentResult,
        action_result: FollowUpActionResult,
        route_decision: TurnRouteDecision,
        blocked_reason: str | None,
    ) -> str:
        if blocked_reason:
            return "blocked"
        if action_result.operation == "expand_target":
            return "action_expand"
        if follow_up_result.operation == "subset":
            return "subset"
        if follow_up_result.operation in {"inherit", "replace_slot", "correct_slot", "switch_capability", "drilldown_ref"}:
            return "inherit"
        if str(getattr(route_decision, "route_source", "") or "") == "context":
            return "inherit"
        return "standalone"

    @staticmethod
    def _subject_family(
        *,
        route_decision: TurnRouteDecision,
        current_context: dict[str, Any],
        query_profile: QueryProfile,
        normalized_text: str,
    ) -> str:
        query_shape = getattr(route_decision, "query_shape", None)
        subject = str(getattr(query_shape, "subject", "") or "")
        if (
            query_profile.data_focus == "warning_only"
            and subject == "soil"
            and any(token in normalized_text for token in ("重点关注", "需要关注", "预警"))
        ):
            return "warning"
        if subject:
            return "warning" if subject == "warning_rule" else subject
        topic_family = str(current_context.get("topic_family") or "")
        return topic_family or "soil"

    @classmethod
    def _answer_intent(
        cls,
        *,
        route_decision: TurnRouteDecision,
        follow_up_result: FollowUpIntentResult,
        current_context: dict[str, Any],
        query_profile: QueryProfile,
        normalized_text: str,
    ) -> str:
        chosen_target = follow_up_result.chosen_target or cls._latest_target(current_context)
        if follow_up_result.operation == "subset":
            inherited_intent = cls._intent_from_target(chosen_target)
            if inherited_intent:
                return inherited_intent
        query_shape = getattr(route_decision, "query_shape", None)
        action = str(getattr(query_shape, "action", "") or "")
        if (
            query_profile.data_focus == "warning_only"
            and action == "summary"
            and any(token in normalized_text for token in ("重点关注", "需要关注", "预警"))
            and any(token in normalized_text for token in ("地区", "区域", "地方"))
        ):
            return "group"
        if action:
            return action
        inherited_intent = cls._intent_from_target(chosen_target)
        return inherited_intent or "summary"

    @staticmethod
    def _intent_from_target(target: dict[str, Any] | None) -> str | None:
        if not target:
            return None
        capability = str(target.get("capability") or "")
        grain = str(target.get("grain") or "")
        mapping = {
            "summary": "summary",
            "detail": "detail",
            "list": "list",
            "group": "group",
            "count": "count",
            "compare": "compare",
            "warning_group": "group",
            "warning_list": "list",
            "warning_count": "count",
            "warning_disposal": "disposal",
            "device_registry_distribution": "distribution",
        }
        if capability in mapping:
            return mapping[capability]
        if grain == "region_group":
            return "group"
        if grain in {"record_list", "device_list"}:
            return "list"
        if grain == "entity_detail":
            return "detail"
        return None

    @classmethod
    def _group_by(
        cls,
        *,
        route_decision: TurnRouteDecision,
        follow_up_result: FollowUpIntentResult,
        subject_family: str,
        answer_intent: str,
        normalized_text: str,
    ) -> str | None:
        if (
            subject_family == "warning"
            and answer_intent == "group"
            and any(token in normalized_text for token in ("地区", "区域", "地方"))
        ):
            return "region"
        if getattr(route_decision, "group_by", None):
            return route_decision.group_by
        chosen_target = follow_up_result.chosen_target
        if not chosen_target:
            return None
        grain = str(chosen_target.get("grain") or "")
        if grain == "region_group":
            return "region"
        return None

    @staticmethod
    def _measure(
        *,
        query_profile: QueryProfile,
        subject_family: str,
        answer_intent: str,
        normalized_text: str,
    ) -> str | None:
        if query_profile.measure:
            return query_profile.measure
        if (
            query_profile.data_focus == "warning_only"
            and subject_family == "warning"
            and answer_intent == "group"
            and any(token in normalized_text for token in ("重点关注", "需要关注", "预警"))
        ):
            return "alert_device_count"
        return None

    @staticmethod
    def _time_window_dict(time_evidence: Any | None) -> dict[str, Any]:
        start_time = getattr(time_evidence, "start_time", None)
        end_time = getattr(time_evidence, "end_time", None)
        if not start_time and not end_time:
            return {}
        return {
            "start_time": start_time,
            "end_time": end_time,
        }


__all__ = ["TurnInterpretation", "TurnInterpretationService"]

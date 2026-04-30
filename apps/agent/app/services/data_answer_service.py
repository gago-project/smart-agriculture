"""Deterministic soil-data answer service for server-backed chat sessions."""

from __future__ import annotations


import asyncio
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.repositories.result_snapshot_repository import ResultSnapshotRepository
from app.repositories.soil_repository import DatabaseQueryError, SoilRepository
from app.services.follow_up_intent_resolver_service import (
    FOLLOW_UP_MAX_TURN_GAP,
    FollowUpIntentResolverService,
    FollowUpIntentResult,
)
from app.services.follow_up_action_resolver_service import FollowUpActionResolverService
from app.services.input_guard_service import InputGuardService
from app.services.llm_follow_up_resolver_service import LlmFollowUpResolution, LlmFollowUpResolverService
from app.services.llm_input_guard_service import LlmInputGuardService
from app.services.parameter_resolver_service import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    ParameterResolverService,
)
from app.services.time_window_service import TimeWindowService
from app.services.turn_route_decision_service import TurnRouteDecisionService


SN_PATTERN = re.compile(r"SNS\d{8}", re.IGNORECASE)
LIST_TARGET_FOCUS_DEVICES = "devices"
LIST_TARGET_ALERT_RECORDS = "records"
FOCUS_DEVICE_COLUMNS = ["city", "county", "sn", "create_time", "water20cm", "t20cm"]
ALERT_RECORD_COLUMNS = ["create_time", "city", "county", "sn", "water20cm", "t20cm"]
REGION_GROUP_COLUMNS = ["city", "county"]
CITY_GROUP_COLUMNS = ["city"]
DERIVED_QUERY_KEYS = {"soil_status", "warning_level", "risk_score", "display_label", "rule_version"}
RAW_SOIL_KEYS = {
    "id",
    "sn",
    "gatewayid",
    "sensorid",
    "unitid",
    "time",
    "water20cm",
    "water40cm",
    "water60cm",
    "water80cm",
    "t20cm",
    "t40cm",
    "t60cm",
    "t80cm",
    "water20cmfieldstate",
    "water40cmfieldstate",
    "water60cmfieldstate",
    "water80cmfieldstate",
    "t20cmfieldstate",
    "t40cmfieldstate",
    "t60cmfieldstate",
    "t80cmfieldstate",
    "create_time",
    "lat",
    "lon",
    "city",
    "county",
}
DOMAIN_INTENT_TOKENS = (
    "墒情",
    "预警",
    "异常",
    "情况",
    "数据",
    "点位",
    "设备",
    "记录",
    "详情",
    "明细",
    "排名",
    "严重",
    "规则",
    "模板",
    "模版",
)
TIME_ONLY_FOLLOW_UP_PATTERNS = (
    re.compile(r"^(?:最近|近|过去|前)?\s*[0-9一二两三四五六七八九十百]+\s*(?:天|周|月|年|个月)\s*(?:呢)?$", re.IGNORECASE),
    re.compile(r"^(?:今天|昨天|前天|上周|这周|本周|这个月|本月|上个月|今年|最近)\s*(?:呢)?$", re.IGNORECASE),
)
CONTEXTUAL_FOLLOW_UP_MARKERS = ("这些", "这里", "这里的", "上面的", "刚才", "那个情况", "这种情况", "那边", "这边")
GLOBAL_SCOPE_RESET_MARKERS = ("整体", "全省", "整个", "全部", "哪里", "哪个地方", "最严重", "排名", "排行", "top", "Top", "哪些地方", "哪些地区")
LLM_GUARD_CONFIDENCE_THRESHOLD = 0.8
SAFE_HINT_TEXT = "我可以帮你查墒情概况、地区/点位/记录明细、按地区汇总，以及查看预警规则和模板。你可以直接说地区、设备或时间范围，例如：南京最近7天墒情怎么样，或最近30天按地区汇总墒情数据。"
UNSUPPORTED_DERIVED_ANALYSIS_TEXT = "当前查询只支持原始墒情数据和直接统计，不支持“异常最多、风险最高、预警排序”这类衍生判断。你可以改问：最近30天按地区汇总墒情数据，或直接查看当前预警规则。"
LLM_GUARD_DOMAIN_TOKENS = DOMAIN_INTENT_TOKENS + ("土壤", "含水量")
QUERY_CUE_TOKENS = ("查", "看", "情况", "怎么样", "有没有问题", "需要", "最近", "最新")
REGION_GROUP_REQUEST_PATTERNS = (
    re.compile(r"(覆盖|涉及).*(地方|地区|区域)"),
    re.compile(r"((?:有|又)?哪些|哪[0-9一二两三四五六七八九十百]*个).*(地方|地区|区域)"),
    re.compile(r"^[0-9一二两三四五六七八九十百]+\s*个?\s*(地方|地区|区域)(?:呢|详情|明细)?$"),
    re.compile(r"^(这些|这几个|那些|上面的)\s*(地方|地区|区域)(?:呢|详情|明细)?$"),
)
CONTEXT_VERSION = 3
RESULT_REF_LIMIT = 20
FOLLOW_UP_TARGET_LIMIT = 5
DETAIL_HINT_TOKENS = ("详情", "明细")
LIST_ENUMERATION_TOKENS = ("哪些", "哪几个", "有哪些")
TEMPLATE_TOKENS = ("模板", "模版")
LIST_TABLE_PAGE_SIZE = 10


logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    """Convert numbers into float when possible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class DataAnswerService:
    """Render stable business answers from soil records, snapshots, rules, and templates."""

    def __init__(
        self,
        repository: SoilRepository | Any | None = None,
        snapshot_repository: ResultSnapshotRepository | None = None,
        input_guard: InputGuardService | None = None,
        llm_input_guard: LlmInputGuardService | Any | None = None,
        llm_follow_up_resolver: LlmFollowUpResolverService | Any | None = None,
        follow_up_action_resolver: FollowUpActionResolverService | None = None,
        time_window_service: TimeWindowService | None = None,
        parameter_resolver: ParameterResolverService | None = None,
        follow_up_intent_resolver: FollowUpIntentResolverService | None = None,
        turn_route_decision_service: TurnRouteDecisionService | None = None,
    ) -> None:
        self.repository = repository or SoilRepository.from_env()
        self.snapshot_repository = snapshot_repository or ResultSnapshotRepository(self.repository)
        self.input_guard = input_guard or InputGuardService()
        self.llm_input_guard = llm_input_guard
        self.llm_follow_up_resolver = llm_follow_up_resolver
        self.follow_up_action_resolver = follow_up_action_resolver or FollowUpActionResolverService()
        self.time_window_service = time_window_service or TimeWindowService()
        self.parameter_resolver = parameter_resolver or ParameterResolverService(self.repository)
        self.follow_up_intent_resolver = follow_up_intent_resolver or FollowUpIntentResolverService()
        self.turn_route_decision_service = turn_route_decision_service or TurnRouteDecisionService()

    async def reply(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any] | None,
        timezone: str = "Asia/Shanghai",
    ) -> dict[str, Any]:
        """Handle one deterministic data-answer turn."""
        del timezone
        text = (message or "").strip()
        context = self._normalize_context(current_context)
        guard = self.input_guard.classify(text)
        if not guard.allow_business_flow:
            next_context = context
            if guard.guidance_reason == "closing":
                next_context = self._closed_turn_context(turn_id)
            return self._build_guidance_response(
                turn_id=turn_id,
                text=guard.suggested_answer,
                current_context=next_context,
                guidance_reason=guard.guidance_reason or "safe_hint",
                conversation_closed=guard.guidance_reason == "closing",
            )

        entities = await self._extract_entities(text)
        latest_business_time = await self._latest_business_time()
        time_evidence = self.time_window_service.resolve(text, latest_business_time)
        action_result = self.follow_up_action_resolver.resolve(
            text=text,
            current_context=context,
            turn_id=turn_id,
        )
        route_decision = self.turn_route_decision_service.decide(
            message=text,
            current_context=context,
            entities=entities,
            time_evidence=time_evidence,
            action_result=action_result,
        )
        logger.info(
            "turn route session_id=%s turn_id=%s route=%s source=%s normalized_text=%s reasons=%s list_target=%s group_by=%s query_shape=%s/%s/%s/%s action_operation=%s",
            session_id,
            turn_id,
            route_decision.route,
            route_decision.route_source,
            route_decision.normalized_text,
            list(route_decision.reason_codes),
            route_decision.list_target,
            route_decision.group_by,
            route_decision.query_shape.subject,
            route_decision.query_shape.action,
            route_decision.query_shape.grain,
            route_decision.query_shape.mode,
            action_result.operation,
        )

        if route_decision.route == "rule":
            return await self._reply_rule(message=text, session_id=session_id, turn_id=turn_id, current_context=context)
        if route_decision.route == "template":
            return await self._reply_template(message=text, session_id=session_id, turn_id=turn_id, current_context=context)
        if route_decision.route == "unsupported_derived":
            return self._build_guidance_response(
                turn_id=turn_id,
                text=UNSUPPORTED_DERIVED_ANALYSIS_TEXT,
                current_context=context,
                guidance_reason="clarification",
            )
        if route_decision.route == "explicit_detail":
            return await self._reply_detail(message=text, session_id=session_id, turn_id=turn_id, current_context=context)
        if route_decision.route == "standalone_group":
            return await self._reply_group(
                message=text,
                session_id=session_id,
                turn_id=turn_id,
                current_context=context,
                resolved_group_by=route_decision.group_by,
            )
        if route_decision.route == "standalone_list":
            return await self._reply_standalone_list(
                message=text,
                session_id=session_id,
                turn_id=turn_id,
                current_context=context,
                list_target=route_decision.list_target or LIST_TARGET_FOCUS_DEVICES,
            )
        if route_decision.route == "follow_up_action_clarify":
            logger.info(
                "follow-up action session_id=%s turn_id=%s context_version=%s operation=%s matched_action_target_key=%s subject_kind=%s parsed_count=%s target_count=%s fallback_path=%s clarify_reason=%s",
                session_id,
                turn_id,
                context.get("context_version"),
                action_result.operation,
                None,
                action_result.subject_kind,
                action_result.parsed_count,
                None,
                "clarify",
                action_result.clarify_reason,
            )
            return self._build_guidance_response(
                turn_id=turn_id,
                text=action_result.clarify_message,
                current_context=context,
                guidance_reason="clarification",
            )
        if route_decision.route == "follow_up_action_expand":
            selected_target = action_result.selected_action_target or {}
            logger.info(
                "follow-up action session_id=%s turn_id=%s context_version=%s operation=%s matched_action_target_key=%s subject_kind=%s parsed_count=%s target_count=%s fallback_path=%s clarify_reason=%s",
                session_id,
                turn_id,
                context.get("context_version"),
                action_result.operation,
                selected_target.get("target_key"),
                action_result.subject_kind,
                action_result.parsed_count,
                selected_target.get("count"),
                "action_target",
                action_result.clarify_reason,
            )
            return await self._reply_from_action_target(
                message=text,
                session_id=session_id,
                turn_id=turn_id,
                current_context=context,
                action_target=selected_target,
            )

        if route_decision.route == "follow_up_list":
            return await self._reply_list(
                message=text,
                session_id=session_id,
                turn_id=turn_id,
                current_context=context,
                list_target=route_decision.list_target or LIST_TARGET_FOCUS_DEVICES,
            )
        if route_decision.route == "follow_up_group":
            return await self._reply_group(
                message=text,
                session_id=session_id,
                turn_id=turn_id,
                current_context=context,
                resolved_group_by=route_decision.group_by,
            )

        if route_decision.route == "compare":
            return await self._reply_compare(message=text, session_id=session_id, turn_id=turn_id, current_context=context)

        if route_decision.route == "follow_up_detail":
            return await self._reply_detail(message=text, session_id=session_id, turn_id=turn_id, current_context=context)

        if route_decision.route == "detail":
            return await self._reply_detail(message=text, session_id=session_id, turn_id=turn_id, current_context=context)

        if route_decision.route == "safe_hint":
            return self._build_guidance_response(
                turn_id=turn_id,
                text=SAFE_HINT_TEXT,
                current_context=context,
                guidance_reason="safe_hint",
            )

        llm_guard_result = await self._maybe_run_llm_input_guard(
            text=text,
            context=context,
            session_id=session_id,
            turn_id=turn_id,
        )
        if llm_guard_result is not None:
            return llm_guard_result

        return await self._reply_summary(message=text, session_id=session_id, turn_id=turn_id, current_context=context)

    def _normalize_context(self, current_context: dict[str, Any] | None) -> dict[str, Any]:
        context = current_context if isinstance(current_context, dict) else {}
        if context.get("closed"):
            return self._closed_turn_context(int(context.get("last_closed_turn_id") or context.get("active_topic_turn_id") or 0))
        derived_sets = dict(context.get("derived_sets") or {})
        if derived_sets.get("focus_devices_snapshot_id") and not derived_sets.get("device_snapshot_id"):
            derived_sets["device_snapshot_id"] = derived_sets["focus_devices_snapshot_id"]
        if derived_sets.get("alert_records_snapshot_id") and not derived_sets.get("record_snapshot_id"):
            derived_sets["record_snapshot_id"] = derived_sets["alert_records_snapshot_id"]
        normalized = {
            "context_version": CONTEXT_VERSION,
            "topic_family": context.get("topic_family"),
            "active_topic_turn_id": context.get("active_topic_turn_id"),
            "primary_block_id": context.get("primary_block_id"),
            "primary_query_spec": context.get("primary_query_spec") or {},
            "time_window": context.get("time_window") or {},
            "resolved_entities": context.get("resolved_entities") or [],
            "derived_sets": derived_sets,
            "compare_winner_entity": context.get("compare_winner_entity"),
            "closed": False,
            "query_state": context.get("query_state"),
            "follow_up_targets": list(context.get("follow_up_targets") or []),
            "result_refs": list(context.get("result_refs") or []),
            "action_targets": list(context.get("action_targets") or []),
            "last_closed_turn_id": context.get("last_closed_turn_id"),
        }
        if normalized["query_state"] is None:
            normalized["query_state"] = self._legacy_query_state(normalized)
        if not normalized["follow_up_targets"] and normalized["query_state"]:
            normalized["follow_up_targets"] = [self._follow_up_target_from_query_state(normalized["query_state"])]
        if not normalized["action_targets"]:
            normalized["action_targets"] = self._legacy_action_targets(normalized)
        normalized["follow_up_targets"] = [target for target in normalized["follow_up_targets"] if isinstance(target, dict)][
            :FOLLOW_UP_TARGET_LIMIT
        ]
        normalized["result_refs"] = [ref for ref in normalized["result_refs"] if isinstance(ref, dict)][:RESULT_REF_LIMIT]
        normalized["action_targets"] = [target for target in normalized["action_targets"] if isinstance(target, dict)]
        return normalized

    @staticmethod
    def _empty_turn_context() -> dict[str, Any]:
        return {
            "context_version": CONTEXT_VERSION,
            "topic_family": None,
            "active_topic_turn_id": None,
            "primary_block_id": None,
            "primary_query_spec": {},
            "time_window": {},
            "resolved_entities": [],
            "derived_sets": {},
            "compare_winner_entity": None,
            "closed": False,
            "query_state": None,
            "follow_up_targets": [],
            "result_refs": [],
            "action_targets": [],
            "last_closed_turn_id": None,
        }

    @classmethod
    def _closed_turn_context(cls, turn_id: int) -> dict[str, Any]:
        context = cls._empty_turn_context()
        context["closed"] = True
        context["last_closed_turn_id"] = turn_id or None
        return context

    def _legacy_query_state(self, context: dict[str, Any]) -> dict[str, Any] | None:
        if context.get("topic_family") != "data":
            return None
        primary_query_spec = context.get("primary_query_spec") or {}
        capability = primary_query_spec.get("capability") or "summary"
        grain = primary_query_spec.get("grain") or "aggregate"
        slots = self._slots_from_context(context)
        slot_confidence = {
            key: CONFIDENCE_HIGH for key, value in slots.items() if value
        }
        if context.get("time_window", {}).get("start_time") and context.get("time_window", {}).get("end_time"):
            slot_confidence["time"] = CONFIDENCE_HIGH
        slot_source = {
            key: "explicit" for key, value in slots.items() if value
        }
        if slot_confidence.get("time"):
            slot_source["time"] = "explicit"
        return {
            "intent": capability,
            "capability": capability,
            "grain": grain,
            "slots": slots,
            "slot_confidence": slot_confidence,
            "slot_source": slot_source,
            "time_window": context.get("time_window") or {},
            "source_turn_id": context.get("active_topic_turn_id"),
            "last_active_turn_id": context.get("active_topic_turn_id"),
        }

    @staticmethod
    def _slots_from_resolved_args(resolved_args: dict[str, Any]) -> dict[str, Any]:
        return {
            "province": resolved_args.get("province"),
            "city": resolved_args.get("city"),
            "county": resolved_args.get("county"),
            "sn": resolved_args.get("sn"),
        }

    @staticmethod
    def _slots_from_resolved_entities(resolved_entities: list[dict[str, Any]]) -> dict[str, Any]:
        slots = {"province": None, "city": None, "county": None, "sn": None}
        for entity in resolved_entities:
            kind = entity.get("kind")
            canonical_name = entity.get("canonical_name")
            if kind == "province":
                slots["province"] = canonical_name
            elif kind == "city":
                slots["city"] = canonical_name
            elif kind == "county":
                slots["county"] = canonical_name
            elif kind == "device":
                slots["sn"] = canonical_name
        return slots

    def _slots_from_context(self, context: dict[str, Any]) -> dict[str, Any]:
        query_state = context.get("query_state") or {}
        if query_state.get("slots"):
            slots = dict(query_state.get("slots") or {})
            return {
                "province": slots.get("province"),
                "city": slots.get("city"),
                "county": slots.get("county"),
                "sn": slots.get("sn"),
            }
        primary_query_spec = context.get("primary_query_spec") or {}
        entities = primary_query_spec.get("entities") or {}
        slots = {
            "province": None,
            "city": next(iter(entities.get("city") or []), None),
            "county": next(iter(entities.get("county") or []), None),
            "sn": next(iter(entities.get("sn") or []), None),
        }
        if not any(slots.values()):
            return self._slots_from_resolved_entities(context.get("resolved_entities") or [])
        return slots

    @staticmethod
    def _follow_up_target_from_query_state(query_state: dict[str, Any], *, parent_target_key: str | None = None) -> dict[str, Any]:
        source_turn_id = query_state.get("source_turn_id") or query_state.get("last_active_turn_id")
        capability = query_state.get("capability") or "summary"
        return {
            "target_key": f"target_{source_turn_id}_{capability}",
            "capability": capability,
            "grain": query_state.get("grain"),
            "slots": query_state.get("slots") or {},
            "slot_confidence": query_state.get("slot_confidence") or {},
            "slot_source": query_state.get("slot_source") or {},
            "time_window": query_state.get("time_window") or {},
            "source_turn_id": source_turn_id,
            "last_active_turn_id": query_state.get("last_active_turn_id") or source_turn_id,
            "parent_target_key": parent_target_key,
        }

    def _latest_follow_up_target(self, context: dict[str, Any]) -> dict[str, Any] | None:
        targets = context.get("follow_up_targets") or []
        return targets[0] if targets else None

    @staticmethod
    def _action_target(
        *,
        target_key: str,
        capability: str,
        grain: str,
        subject_kind: str,
        source_snapshot_id: str | None,
        source_snapshot_kind: str | None,
        group_by: str | None,
        count: int | None,
        label: str,
        source_turn_id: int,
        last_active_turn_id: int,
    ) -> dict[str, Any]:
        return {
            "target_key": target_key,
            "capability": capability,
            "grain": grain,
            "subject_kind": subject_kind,
            "source_snapshot_id": source_snapshot_id,
            "source_snapshot_kind": source_snapshot_kind,
            "group_by": group_by,
            "count": count,
            "label": label,
            "source_turn_id": source_turn_id,
            "last_active_turn_id": last_active_turn_id,
        }

    def _legacy_action_targets(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        if context.get("topic_family") != "data" or context.get("closed"):
            return []
        derived_sets = context.get("derived_sets") or {}
        primary_query_spec = context.get("primary_query_spec") or {}
        capability = str(primary_query_spec.get("capability") or "")
        grain = str(primary_query_spec.get("grain") or "")
        source_turn_id = int(context.get("active_topic_turn_id") or 0)
        targets: list[dict[str, Any]] = []
        focus_snapshot_id = derived_sets.get("device_snapshot_id") or derived_sets.get("focus_devices_snapshot_id")
        alert_snapshot_id = derived_sets.get("record_snapshot_id") or derived_sets.get("alert_records_snapshot_id")

        if capability == "summary":
            if alert_snapshot_id:
                targets.append(
                    self._action_target(
                        target_key=f"target_{source_turn_id}_alert_records",
                        capability="list",
                        grain="record_list",
                        subject_kind="record",
                        source_snapshot_id=alert_snapshot_id,
                        source_snapshot_kind=LIST_TARGET_ALERT_RECORDS,
                        group_by=None,
                        count=None,
                        label="记录",
                        source_turn_id=source_turn_id,
                        last_active_turn_id=source_turn_id,
                    )
                )
            if focus_snapshot_id:
                targets.extend(
                    [
                        self._action_target(
                            target_key=f"target_{source_turn_id}_focus_devices",
                            capability="list",
                            grain="device_list",
                            subject_kind="device",
                            source_snapshot_id=focus_snapshot_id,
                            source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                            group_by=None,
                            count=None,
                            label="点位",
                            source_turn_id=source_turn_id,
                            last_active_turn_id=source_turn_id,
                        ),
                        self._action_target(
                            target_key=f"target_{source_turn_id}_covered_regions",
                            capability="group",
                            grain="region_group",
                            subject_kind="region",
                            source_snapshot_id=focus_snapshot_id,
                            source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                            group_by="region",
                            count=None,
                            label="地区",
                            source_turn_id=source_turn_id,
                            last_active_turn_id=source_turn_id,
                        ),
                    ]
                )
            return targets

        if capability == "compare" and focus_snapshot_id:
            return [
                self._action_target(
                    target_key=f"target_{source_turn_id}_winner_focus_devices",
                    capability="list",
                    grain="device_list",
                    subject_kind="device",
                    source_snapshot_id=focus_snapshot_id,
                    source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                    group_by=None,
                    count=None,
                    label="点位",
                    source_turn_id=source_turn_id,
                    last_active_turn_id=source_turn_id,
                )
            ]

        if capability == "list" or grain in {"record_list", "device_list"}:
            if grain == "record_list" and alert_snapshot_id:
                return [
                    self._action_target(
                        target_key=f"target_{source_turn_id}_covered_regions",
                        capability="group",
                        grain="region_group",
                        subject_kind="region",
                        source_snapshot_id=alert_snapshot_id,
                        source_snapshot_kind=LIST_TARGET_ALERT_RECORDS,
                        group_by="region",
                        count=None,
                        label="地区",
                        source_turn_id=source_turn_id,
                        last_active_turn_id=source_turn_id,
                    )
                ]
            if focus_snapshot_id:
                return [
                    self._action_target(
                        target_key=f"target_{source_turn_id}_covered_regions",
                        capability="group",
                        grain="region_group",
                        subject_kind="region",
                        source_snapshot_id=focus_snapshot_id,
                        source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                        group_by="region",
                        count=None,
                        label="地区",
                        source_turn_id=source_turn_id,
                        last_active_turn_id=source_turn_id,
                    )
                ]
        return []

    def _merge_follow_up_targets(
        self,
        *,
        current_context: dict[str, Any],
        query_state: dict[str, Any] | None,
        parent_target_key: str | None,
        replace_history: bool = False,
    ) -> list[dict[str, Any]]:
        if not query_state:
            return []
        next_target = self._follow_up_target_from_query_state(query_state, parent_target_key=parent_target_key)
        if replace_history:
            return [next_target]
        merged = [next_target]
        for target in current_context.get("follow_up_targets") or []:
            if target.get("target_key") == next_target["target_key"]:
                continue
            merged.append(target)
            if len(merged) >= FOLLOW_UP_TARGET_LIMIT:
                break
        return merged

    @staticmethod
    def _slot_confidence_map(*, slots: dict[str, Any], entity_confidence: str, time_confidence: str) -> dict[str, str]:
        mapping = {key: entity_confidence for key, value in slots.items() if value}
        if time_confidence:
            mapping["time"] = time_confidence
        return mapping

    @staticmethod
    def _slot_source_map(
        *,
        slots: dict[str, Any],
        explicit_slots: set[str],
        inherited_slots: set[str],
        corrected_slots: set[str],
        time_source: str,
        operation: str,
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for key, value in slots.items():
            if not value:
                continue
            if key in corrected_slots:
                mapping[key] = "corrected"
            elif key in explicit_slots:
                mapping[key] = "explicit"
            elif key in inherited_slots:
                mapping[key] = "inherited"
            else:
                mapping[key] = "explicit" if operation == "standalone" else "inherited"
        mapping["time"] = "inherited" if time_source == "history_inherited" else "explicit"
        if operation == "correct_slot" and mapping.get("time") == "explicit" and time_source == "history_inherited":
            mapping["time"] = "corrected"
        return mapping

    def _build_query_state(
        self,
        *,
        turn_id: int,
        capability: str,
        grain: str,
        slots: dict[str, Any],
        time_window: dict[str, Any],
        slot_confidence: dict[str, str],
        slot_source: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "intent": capability,
            "capability": capability,
            "grain": grain,
            "slots": slots,
            "slot_confidence": slot_confidence,
            "slot_source": slot_source,
            "time_window": time_window,
            "source_turn_id": turn_id,
            "last_active_turn_id": turn_id,
        }

    def _build_result_refs(self, *, turn_id: int, block: dict[str, Any]) -> list[dict[str, Any]]:
        block_type = block.get("block_type")
        refs: list[dict[str, Any]] = []
        if block_type == "summary_card":
            for idx, row in enumerate(block.get("top_regions") or [], start=1):
                label = str(row.get("county") or row.get("city") or "").strip()
                if not label:
                    continue
                refs.append(
                    {
                        "ref_key": f"ref_{turn_id}_{idx}",
                        "target_key": None,
                        "ref_type": "region",
                        "label": label,
                        "ordinal": idx,
                        "entity_payload": {"city": row.get("city"), "county": row.get("county")},
                        "source_turn_id": turn_id,
                    }
                )
        elif block_type == "list_table":
            for idx, row in enumerate(block.get("rows") or [], start=1):
                label = str(row.get("sn") or row.get("county") or row.get("city") or "").strip()
                if not label:
                    continue
                refs.append(
                    {
                        "ref_key": f"ref_{turn_id}_{idx}",
                        "target_key": None,
                        "ref_type": "device" if row.get("sn") else "region",
                        "label": label,
                        "ordinal": idx,
                        "entity_payload": {"city": row.get("city"), "county": row.get("county"), "sn": row.get("sn")},
                        "source_turn_id": turn_id,
                    }
                )
        elif block_type == "group_table":
            group_by = block.get("group_by")
            for idx, row in enumerate(block.get("rows") or [], start=1):
                if group_by != "region":
                    continue
                city = str(row.get("city") or "").strip()
                county = str(row.get("county") or "").strip()
                label = f"{city}-{county}" if city and county else city or county
                if not label:
                    continue
                refs.append(
                    {
                        "ref_key": f"ref_{turn_id}_{idx}",
                        "target_key": None,
                        "ref_type": "region",
                        "label": label,
                        "ordinal": idx,
                        "entity_payload": {"city": city, "county": county},
                        "source_turn_id": turn_id,
                    }
                )
        elif block_type == "detail_card":
            latest_record = block.get("latest_record") or {}
            label = str(latest_record.get("sn") or block.get("title") or "").strip()
            if label:
                refs.append(
                    {
                        "ref_key": f"ref_{turn_id}_1",
                        "target_key": None,
                        "ref_type": "device" if latest_record.get("sn") else "region",
                        "label": label,
                        "ordinal": 1,
                        "entity_payload": {
                            "city": latest_record.get("city"),
                            "county": latest_record.get("county"),
                            "sn": latest_record.get("sn"),
                        },
                        "source_turn_id": turn_id,
                    }
                )
        elif block_type == "compare_card":
            for idx, row in enumerate(block.get("rows") or [], start=1):
                entity = str(row.get("entity") or "").strip()
                if not entity:
                    continue
                refs.append(
                    {
                        "ref_key": f"ref_{turn_id}_{idx}",
                        "target_key": None,
                        "ref_type": "region",
                        "label": entity,
                        "ordinal": idx,
                        "entity_payload": {
                            "city": entity if entity.endswith("市") else None,
                            "county": entity if entity.endswith(("县", "区")) else None,
                            "sn": entity if entity.startswith("SNS") else None,
                        },
                        "source_turn_id": turn_id,
                    }
                )
        return refs[:RESULT_REF_LIMIT]

    def _build_summary_action_targets(
        self,
        *,
        turn_id: int,
        block: dict[str, Any],
    ) -> list[dict[str, Any]]:
        metrics = block.get("metrics") or {}
        return [
            self._action_target(
                target_key=f"target_{turn_id}_records",
                capability="list",
                grain="record_list",
                subject_kind="record",
                source_snapshot_id=block.get("record_snapshot_id"),
                source_snapshot_kind=LIST_TARGET_ALERT_RECORDS,
                group_by=None,
                count=int(metrics.get("record_count") or 0),
                label=f"{int(metrics.get('record_count') or 0)}条记录",
                source_turn_id=turn_id,
                last_active_turn_id=turn_id,
            ),
            self._action_target(
                target_key=f"target_{turn_id}_devices",
                capability="list",
                grain="device_list",
                subject_kind="device",
                source_snapshot_id=block.get("device_snapshot_id"),
                source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                group_by=None,
                count=int(metrics.get("device_count") or 0),
                label=f"{int(metrics.get('device_count') or 0)}个点位",
                source_turn_id=turn_id,
                last_active_turn_id=turn_id,
            ),
            self._action_target(
                target_key=f"target_{turn_id}_covered_regions",
                capability="group",
                grain="region_group",
                subject_kind="region",
                source_snapshot_id=block.get("device_snapshot_id"),
                source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                group_by="region",
                count=int(metrics.get("region_count") or 0),
                label=f"{int(metrics.get('region_count') or 0)}个地区",
                source_turn_id=turn_id,
                last_active_turn_id=turn_id,
            ),
        ]

    def _build_list_action_targets(
        self,
        *,
        turn_id: int,
        snapshot_id: str | None,
        snapshot_kind: str,
        rows: list[dict[str, Any]],
        device_snapshot_id: str | None = None,
        device_count: int | None = None,
    ) -> list[dict[str, Any]]:
        region_keys = {
            self._group_key_for_row(row, "region")
            for row in rows
            if self._group_key_for_row(row, "region") != "未知"
        }
        targets: list[dict[str, Any]] = []
        if snapshot_kind == LIST_TARGET_ALERT_RECORDS:
            targets.append(
                self._action_target(
                    target_key=f"target_{turn_id}_records",
                    capability="list",
                    grain="record_list",
                    subject_kind="record",
                    source_snapshot_id=snapshot_id,
                    source_snapshot_kind=LIST_TARGET_ALERT_RECORDS,
                    group_by=None,
                    count=len(rows),
                    label=f"{len(rows)}条记录",
                    source_turn_id=turn_id,
                    last_active_turn_id=turn_id,
                )
            )
            if device_snapshot_id:
                targets.append(
                    self._action_target(
                        target_key=f"target_{turn_id}_devices",
                        capability="list",
                        grain="device_list",
                        subject_kind="device",
                        source_snapshot_id=device_snapshot_id,
                        source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                        group_by=None,
                        count=int(device_count or 0),
                        label=f"{int(device_count or 0)}个点位",
                        source_turn_id=turn_id,
                        last_active_turn_id=turn_id,
                    )
                )
        else:
            targets.append(
                self._action_target(
                    target_key=f"target_{turn_id}_devices",
                    capability="list",
                    grain="device_list",
                    subject_kind="device",
                    source_snapshot_id=snapshot_id,
                    source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                    group_by=None,
                    count=len(rows),
                    label=f"{len(rows)}个点位",
                    source_turn_id=turn_id,
                    last_active_turn_id=turn_id,
                )
            )
        targets.append(
            self._action_target(
                target_key=f"target_{turn_id}_covered_regions",
                capability="group",
                grain="region_group",
                subject_kind="region",
                source_snapshot_id=snapshot_id,
                source_snapshot_kind=snapshot_kind,
                group_by="region",
                count=len(region_keys),
                label=f"{len(region_keys)}个地区",
                source_turn_id=turn_id,
                last_active_turn_id=turn_id,
            )
        )
        return targets

    def _build_compare_action_targets(
        self,
        *,
        turn_id: int,
        snapshot_id: str | None,
        count: int,
    ) -> list[dict[str, Any]]:
        return [
            self._action_target(
                target_key=f"target_{turn_id}_devices",
                capability="list",
                grain="device_list",
                subject_kind="device",
                source_snapshot_id=snapshot_id,
                source_snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
                group_by=None,
                count=count,
                label=f"{count}个点位",
                source_turn_id=turn_id,
                last_active_turn_id=turn_id,
            )
        ]

    def _finalize_context(
        self,
        *,
        base_context: dict[str, Any],
        current_context: dict[str, Any],
        turn_id: int,
        query_state: dict[str, Any] | None = None,
        parent_target_key: str | None = None,
        result_refs: list[dict[str, Any]] | None = None,
        action_targets: list[dict[str, Any]] | None = None,
        replace_history: bool = False,
    ) -> dict[str, Any]:
        next_context = {
            **self._empty_turn_context(),
            **base_context,
            "context_version": CONTEXT_VERSION,
            "closed": False,
            "last_closed_turn_id": None,
        }
        if next_context.get("topic_family") == "data":
            next_context["query_state"] = query_state
            next_context["follow_up_targets"] = self._merge_follow_up_targets(
                current_context=current_context,
                query_state=query_state,
                parent_target_key=parent_target_key,
                replace_history=replace_history,
            )
            next_context["result_refs"] = result_refs or []
            next_context["action_targets"] = action_targets or []
            target_key = next_context["follow_up_targets"][0]["target_key"] if next_context["follow_up_targets"] else None
            for ref in next_context["result_refs"]:
                ref["target_key"] = target_key
        else:
            next_context["query_state"] = None
            next_context["follow_up_targets"] = []
            next_context["result_refs"] = []
            next_context["action_targets"] = []
        return next_context

    @staticmethod
    def _topic_payload(turn_context: dict[str, Any]) -> dict[str, Any]:
        return {
            "topic_family": turn_context.get("topic_family"),
            "active_topic_turn_id": turn_context.get("active_topic_turn_id"),
            "primary_block_id": turn_context.get("primary_block_id"),
        }

    def _build_guidance_response(
        self,
        *,
        turn_id: int,
        text: str,
        current_context: dict[str, Any],
        guidance_reason: str,
        conversation_closed: bool = False,
    ) -> dict[str, Any]:
        return {
            "turn_id": turn_id,
            "answer_kind": "guidance",
            "capability": "none",
            "final_text": text,
            "blocks": [
                {
                    "block_id": f"block_guidance_{turn_id}",
                    "block_type": "guidance_card",
                    "text": text,
                    "guidance_reason": guidance_reason,
                }
            ],
            "topic": self._topic_payload(current_context),
            "turn_context": current_context,
            "query_ref": {"has_query": False, "snapshot_ids": []},
            "conversation_closed": conversation_closed,
            "session_reset": False,
            "query_log_entries": [],
        }

    async def _build_filter_clarification_response(
        self,
        *,
        message: str,
        turn_id: int,
        current_context: dict[str, Any],
        capability: str,
        grain: str,
        clarify_text: str,
    ) -> dict[str, Any]:
        extracted = await self._extract_entities(message)
        resolved_entities = self._clarification_resolved_entities(extracted, current_context)
        inherited_mode = "inherit" if current_context.get("topic_family") == "data" else "standalone"
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": None,
            "primary_query_spec": self._build_partial_query_spec(
                capability=capability,
                grain=grain,
                source_turn_id=turn_id,
                follow_up_mode=inherited_mode,
                resolved_entities=resolved_entities,
            ),
            "time_window": {},
            "resolved_entities": resolved_entities,
            "derived_sets": {},
            "compare_winner_entity": None,
            "closed": False,
        }
        slots = self._slots_from_resolved_entities(resolved_entities)
        slot_confidence = self._slot_confidence_map(
            slots=slots,
            entity_confidence=CONFIDENCE_HIGH,
            time_confidence="",
        )
        slot_source = self._slot_source_map(
            slots=slots,
            explicit_slots={key for key, value in slots.items() if value},
            inherited_slots=set(),
            corrected_slots=set(),
            time_source="",
            operation=inherited_mode,
        )
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability=capability,
            grain=grain,
            slots=slots,
            time_window={},
            slot_confidence=slot_confidence,
            slot_source=slot_source,
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=(self._latest_follow_up_target(current_context) or {}).get("target_key"),
            result_refs=[],
        )
        return self._build_guidance_response(
            turn_id=turn_id,
            text=clarify_text,
            current_context=turn_context,
            guidance_reason="clarification",
        )

    @staticmethod
    def _default_recent_window(latest_business_time: str) -> dict[str, str]:
        latest_dt = datetime.strptime(latest_business_time[:19], "%Y-%m-%d %H:%M:%S")
        end_dt = datetime(latest_dt.year, latest_dt.month, latest_dt.day, 23, 59, 59)
        start_dt = end_dt - timedelta(days=6)
        start_dt = datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0)
        return {
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "default_recent_7d",
        }

    @staticmethod
    def _current_list_grain(context: dict[str, Any]) -> str:
        return str((context.get("primary_query_spec") or {}).get("grain") or "")

    @staticmethod
    def _is_unsupported_derived_analysis_request(text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False
        lowered = normalized.lower()
        ranking_markers = ("最多", "最少", "最高", "最低", "排名", "排行", "top")
        if any(token in normalized for token in ("异常", "预警", "风险")) and any(marker in lowered for marker in ranking_markers):
            return True
        if "最严重" in normalized and any(token in normalized for token in ("地方", "地区", "区域", "点位", "设备", "哪里", "哪个")):
            return True
        return False

    async def _reply_from_action_target(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
        action_target: dict[str, Any],
    ) -> dict[str, Any]:
        capability = str(action_target.get("capability") or "")
        source_snapshot_kind = str(action_target.get("source_snapshot_kind") or "")
        source_snapshot_id = action_target.get("source_snapshot_id")
        if capability == "list":
            list_target = (
                LIST_TARGET_ALERT_RECORDS
                if source_snapshot_kind == LIST_TARGET_ALERT_RECORDS
                else LIST_TARGET_FOCUS_DEVICES
            )
            return await self._reply_list(
                message=message,
                session_id=session_id,
                turn_id=turn_id,
                current_context=current_context,
                list_target=list_target,
                resolved_snapshot_id=source_snapshot_id,
                resolved_snapshot_kind=source_snapshot_kind or list_target,
            )
        if capability == "group":
            return await self._reply_group(
                message=message,
                session_id=session_id,
                turn_id=turn_id,
                current_context=current_context,
                resolved_snapshot_id=source_snapshot_id,
                resolved_snapshot_kind=source_snapshot_kind,
                resolved_group_by=str(action_target.get("group_by") or "region"),
            )
        return await self._reply_summary(
            message=message,
            session_id=session_id,
            turn_id=turn_id,
            current_context=current_context,
        )

    async def _can_run_standalone_group_query(self, text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False
        if any(token in normalized for token in ("汇总", "归类", "分组")):
            return True
        if any(token in normalized for token in ("墒情", "数据", "记录", "含水量", "土壤")):
            return True
        latest_business_time = await self._latest_business_time()
        time_evidence = self.time_window_service.resolve(normalized, latest_business_time)
        if getattr(time_evidence, "has_time_signal", False):
            return True
        entities = await self._extract_entities(normalized)
        return any(entities.get(key) for key in ("province", "city", "county", "sn"))

    async def _should_treat_group_request_as_standalone(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
    ) -> bool:
        if current_context.get("topic_family") != "data":
            return await self._can_run_standalone_group_query(text)
        normalized = str(text or "").strip()
        if not normalized:
            return False
        latest_business_time = await self._latest_business_time()
        time_evidence = self.time_window_service.resolve(normalized, latest_business_time)
        if getattr(time_evidence, "has_time_signal", False):
            return True
        entities = await self._extract_entities(normalized)
        if any(entities.get(key) for key in ("province", "city", "county", "sn")):
            return True
        return any(token in normalized for token in ("整体", "全省", "整个", "全部"))

    async def _maybe_run_llm_input_guard(
        self,
        *,
        text: str,
        context: dict[str, Any],
        session_id: str,
        turn_id: int,
    ) -> dict[str, Any] | None:
        if not self.llm_input_guard:
            return None
        if not await self._should_use_llm_input_guard(text, context):
            return None

        result = await self.llm_input_guard.classify(text)
        if result.decision != "intercept" or result.confidence < LLM_GUARD_CONFIDENCE_THRESHOLD:
            return None

        logger.info(
            "LLM input guard intercepted session_id=%s turn_id=%s decision=%s reason=%s confidence=%.2f input_preview=%r",
            session_id,
            turn_id,
            result.decision,
            result.reason,
            result.confidence,
            text[:40],
        )
        return self._build_guidance_response(
            turn_id=turn_id,
            text=SAFE_HINT_TEXT,
            current_context=context,
            guidance_reason="safe_hint",
        )

    async def _should_use_llm_input_guard(self, text: str, context: dict[str, Any]) -> bool:
        if context.get("topic_family") == "data":
            return False
        if SN_PATTERN.search(text):
            return False
        if any(token in text for token in LLM_GUARD_DOMAIN_TOKENS):
            return False
        if context.get("topic_family") in {"rule", "template"} and any(
            token in text for token in ("规则", "这些点位", "点位", "详情", *TEMPLATE_TOKENS)
        ):
            return False

        entities = await self._extract_entities(text)
        has_region_scope = any(entities.get(key) for key in ("province", "city", "county"))
        if has_region_scope and any(token in text for token in QUERY_CUE_TOKENS):
            return False
        return True

    async def _latest_business_time(self) -> str:
        latest = await self.repository.latest_business_time_async()
        return str(latest or "1970-01-01 00:00:00")

    async def _load_alias_rows(self) -> list[dict[str, Any]]:
        try:
            rows = await self.repository.region_alias_rows_async()
            return [row for row in rows if isinstance(row, dict)]
        except Exception:
            return []

    async def _extract_entities(self, text: str) -> dict[str, Any]:
        alias_rows = await self._load_alias_rows()
        region_matches: list[dict[str, Any]] = []
        for row in sorted(alias_rows, key=lambda item: len(str(item.get("alias_name") or "")), reverse=True):
            alias_name = str(row.get("alias_name") or "").strip()
            if not alias_name:
                continue
            match_start = text.rfind(alias_name)
            if match_start < 0:
                continue
            region_level = str(row.get("region_level") or "").strip()
            region_matches.append(
                {
                    "alias_name": alias_name,
                    "canonical_name": str(row.get("canonical_name") or "").strip(),
                    "region_level": region_level,
                    "parent_city_name": row.get("parent_city_name"),
                    "match_start": match_start,
                    "match_length": len(alias_name),
                }
            )
        best_matches: dict[tuple[str, str, Any], dict[str, Any]] = {}
        for item in region_matches:
            key = (item["canonical_name"], item["region_level"], item.get("parent_city_name"))
            existing = best_matches.get(key)
            if existing is None or item["match_start"] > existing["match_start"] or (
                item["match_start"] == existing["match_start"] and item["match_length"] > existing["match_length"]
            ):
                best_matches[key] = item

        deduped = sorted(
            best_matches.values(),
            key=lambda item: (int(item.get("match_start") or -1), -int(item.get("match_length") or 0)),
        )
        seen = set(best_matches)

        if "江苏省" in text or "江苏" in text:
            province_alias = "江苏省" if "江苏省" in text else "江苏"
            province_key = ("江苏省", "province", None)
            if province_key not in seen:
                deduped.append(
                    {
                        "alias_name": province_alias,
                        "canonical_name": "江苏省",
                        "region_level": "province",
                        "parent_city_name": None,
                    }
                )
                seen.add(province_key)

        cities = [item["alias_name"] for item in deduped if item["region_level"] == "city"]
        counties = [item["alias_name"] for item in deduped if item["region_level"] == "county"]
        provinces = [item["canonical_name"] for item in deduped if item["region_level"] == "province"]
        sns = [match.group(0).upper() for match in SN_PATTERN.finditer(text)]
        return {
            "province": provinces,
            "city": cities,
            "county": counties,
            "sn": sns,
            "resolved": deduped,
        }

    @staticmethod
    def _clarification_resolved_entities(
        extracted: dict[str, Any],
        current_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        resolved_entities: list[dict[str, Any]] = []
        for item in extracted.get("resolved") or []:
            region_level = str(item.get("region_level") or "")
            canonical_name = str(item.get("canonical_name") or "")
            if not canonical_name:
                continue
            if region_level == "province":
                resolved_entities.append({"kind": "province", "canonical_name": canonical_name})
            elif region_level == "city":
                resolved_entities.append({"kind": "city", "canonical_name": canonical_name})
            elif region_level == "county":
                resolved_entities.append({"kind": "county", "canonical_name": canonical_name})

        for sn in extracted.get("sn") or []:
            canonical_sn = str(sn or "").strip().upper()
            if canonical_sn:
                resolved_entities.append({"kind": "device", "canonical_name": canonical_sn})

        if resolved_entities:
            return resolved_entities

        return [entity for entity in current_context.get("resolved_entities") or [] if entity.get("canonical_name")]

    @staticmethod
    def _should_inherit_entities_from_context(message: str, time_evidence: Any) -> bool:
        normalized = str(message or "").strip()
        if not normalized:
            return False
        if any(marker in normalized for marker in GLOBAL_SCOPE_RESET_MARKERS):
            return False
        if any(marker in normalized for marker in CONTEXTUAL_FOLLOW_UP_MARKERS):
            return True
        if any(pattern.fullmatch(normalized) for pattern in TIME_ONLY_FOLLOW_UP_PATTERNS):
            return True
        return bool(
            getattr(time_evidence, "has_time_signal", False)
            and normalized.endswith("呢")
            and any(token in normalized for token in DOMAIN_INTENT_TOKENS)
        )

    async def _resolve_follow_up_intent(
        self,
        *,
        message: str,
        current_context: dict[str, Any],
        entities: dict[str, Any],
        time_evidence: Any,
        turn_id: int,
    ) -> FollowUpIntentResult:
        result = self.follow_up_intent_resolver.resolve(
            text=message,
            current_context=current_context,
            extracted_entities={
                "province": entities.get("province") or [],
                "city": entities.get("city") or [],
                "county": entities.get("county") or [],
                "sn": entities.get("sn") or [],
            },
            time_has_signal=bool(getattr(time_evidence, "has_time_signal", False)),
            turn_id=turn_id,
        )
        latest_target = self._latest_follow_up_target(current_context)
        if (
            result.uncertain
            and latest_target
            and self.llm_follow_up_resolver
        ):
            llm_result = await self.llm_follow_up_resolver.resolve(
                text=message,
                context=current_context,
                latest_target=latest_target,
            )
            if llm_result and llm_result.confidence >= 0.75:
                result = self._follow_up_result_from_llm(llm_result, latest_target)
        return result

    @staticmethod
    def _follow_up_result_from_llm(
        llm_result: LlmFollowUpResolution,
        latest_target: dict[str, Any] | None,
    ) -> FollowUpIntentResult:
        return FollowUpIntentResult(
            operation=llm_result.operation,
            confidence=llm_result.confidence,
            chosen_target=latest_target,
            new_slots=llm_result.new_slots,
            inherit_slots=llm_result.inherit_slots,
            uncertain=False,
        )

    @staticmethod
    def _target_has_high_confidence(target: dict[str, Any] | None, slot_name: str) -> bool:
        if not target:
            return False
        confidence = str((target.get("slot_confidence") or {}).get(slot_name) or "")
        source = str((target.get("slot_source") or {}).get(slot_name) or "")
        return confidence == CONFIDENCE_HIGH and source in {"explicit", "corrected"}

    def _inherit_scope_from_target(self, *, raw_args: dict[str, Any], target: dict[str, Any] | None) -> bool:
        if not target:
            return False
        slots = target.get("slots") or {}
        if raw_args.get("province") or raw_args.get("city") or raw_args.get("county") or raw_args.get("sn"):
            return True
        for slot_name in ("province", "county", "city", "sn"):
            if slots.get(slot_name) and self._target_has_high_confidence(target, slot_name):
                raw_args[slot_name] = slots[slot_name]
                return True
        return False

    def _inherited_time_window_from_target(
        self,
        *,
        current_context: dict[str, Any],
        target: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not target:
            return None
        targets_by_key = {
            str(item.get("target_key") or ""): item
            for item in current_context.get("follow_up_targets") or []
            if item.get("target_key")
        }
        cursor = target
        seen: set[str] = set()
        while cursor:
            cursor_key = str(cursor.get("target_key") or "")
            if cursor_key in seen:
                break
            seen.add(cursor_key)
            if self._target_has_high_confidence(cursor, "time"):
                time_window = cursor.get("time_window") or {}
                if time_window.get("start_time") and time_window.get("end_time"):
                    return {
                        "start_time": time_window["start_time"],
                        "end_time": time_window["end_time"],
                    }
            parent_key = str(cursor.get("parent_target_key") or "")
            cursor = targets_by_key.get(parent_key)
        return None

    @staticmethod
    def _scope_clarification_message(operation: str) -> str:
        if operation == "stale_target":
            return "上一次查询上下文已经过期了，请重新说明地区、设备或时间范围。"
        return "这轮要查询的对象还不够明确，请直接告诉我地区、设备或时间范围。"

    async def _resolve_filters(
        self,
        *,
        message: str,
        tool_name: str,
        current_context: dict[str, Any],
        allow_inherit_entities: bool = True,
        turn_id: int,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        latest_business_time = await self._latest_business_time()
        entities = await self._extract_entities(message)
        time_evidence = self.time_window_service.resolve(message, latest_business_time)
        follow_up = await self._resolve_follow_up_intent(
            message=message,
            current_context=current_context,
            entities=entities,
            time_evidence=time_evidence,
            turn_id=turn_id,
        )
        if follow_up.operation == "clarify":
            raise ValueError(follow_up.clarify_message or self._scope_clarification_message(follow_up.clarify_reason))
        raw_args: dict[str, Any] = {}
        if entities["sn"]:
            raw_args["sn"] = entities["sn"][-1]
        if entities["province"]:
            raw_args["province"] = entities["province"][-1]
        if entities["county"]:
            raw_args["county"] = entities["county"][-1]
        elif entities["city"]:
            raw_args["city"] = entities["city"][-1]
        if follow_up.selected_ref:
            payload = follow_up.selected_ref.get("entity_payload") or {}
            if payload.get("sn"):
                raw_args["sn"] = payload["sn"]
            if payload.get("province") and not raw_args.get("province"):
                raw_args["province"] = payload["province"]
            if payload.get("county") and not raw_args.get("county"):
                raw_args["county"] = payload["county"]
            elif payload.get("city") and not raw_args.get("city"):
                raw_args["city"] = payload["city"]
            if any(payload.get(key) for key in ("city", "county", "sn")):
                raw_args["trusted_scope"] = True
        has_explicit_scope = bool(raw_args.get("province") or raw_args.get("county") or raw_args.get("city") or raw_args.get("sn"))
        latest_target = follow_up.chosen_target or self._latest_follow_up_target(current_context)
        if (
            not has_explicit_scope
            and allow_inherit_entities
            and current_context.get("topic_family") == "data"
            and follow_up.operation in {"inherit", "switch_capability", "drilldown_ref"}
        ):
            if not self._inherit_scope_from_target(raw_args=raw_args, target=latest_target):
                raise ValueError("这轮要查询的对象还不够明确，请直接告诉我地区、设备或时间范围。")
        elif (
            not has_explicit_scope
            and allow_inherit_entities
            and current_context.get("topic_family") == "data"
            and follow_up.operation == "replace_slot"
            and self._should_inherit_entities_from_context(message, time_evidence)
        ):
            if not self._inherit_scope_from_target(raw_args=raw_args, target=latest_target):
                raise ValueError("这轮要查询的对象还不够明确，请直接告诉我地区、设备或时间范围。")

        inherited_time_window = None
        if current_context.get("topic_family") == "data" and not getattr(time_evidence, "matched", False):
            inherited_time_window = self._inherited_time_window_from_target(
                current_context=current_context,
                target=latest_target,
            )
            if follow_up.operation in {"inherit", "replace_slot", "correct_slot", "switch_capability", "drilldown_ref"} and inherited_time_window is None:
                raise ValueError("这轮缺少可继承的时间范围，请直接补充具体时间段，例如最近7天或最近1个月。")

        resolved = await self.parameter_resolver.resolve(
            tool_name=tool_name,
            raw_args=raw_args,
            latest_business_time=latest_business_time,
            user_input=message,
            time_evidence=time_evidence,
            inherited_time_window=inherited_time_window,
        )
        if resolved.should_clarify:
            raise ValueError(resolved.clarify_message or "当前查询条件还不够明确，请补充后再试。")

        time_window = {
            "start_time": resolved.resolved_args["start_time"],
            "end_time": resolved.resolved_args["end_time"],
            "source": resolved.time_source or "default_recent_7d",
        }
        resolved_entities: list[dict[str, Any]] = []
        if raw_args.get("province") and not resolved.resolved_args.get("city") and not resolved.resolved_args.get("county") and not resolved.resolved_args.get("sn"):
            resolved_entities.append({"kind": "province", "canonical_name": raw_args["province"]})
        if resolved.resolved_args.get("city"):
            resolved_entities.append({"kind": "city", "canonical_name": resolved.resolved_args["city"]})
        if resolved.resolved_args.get("county"):
            if resolved.resolved_args.get("city") and not any(item["kind"] == "city" for item in resolved_entities):
                resolved_entities.append({"kind": "city", "canonical_name": resolved.resolved_args["city"]})
            resolved_entities.append({"kind": "county", "canonical_name": resolved.resolved_args["county"]})
        if resolved.resolved_args.get("sn"):
            resolved_entities.append({"kind": "device", "canonical_name": resolved.resolved_args["sn"]})
        slots = self._slots_from_resolved_args({**resolved.resolved_args, "province": raw_args.get("province")})
        explicit_slots = {key for key in ("province", "city", "county", "sn") if key in raw_args and raw_args.get(key)}
        inherited_slots = {
            key for key in ("province", "city", "county", "sn")
            if slots.get(key) and key not in explicit_slots
        }
        corrected_slots = set(explicit_slots) if follow_up.operation == "correct_slot" else set()
        context_meta = {
            "slots": slots,
            "entity_confidence": resolved.entity_confidence,
            "time_confidence": resolved.time_confidence,
            "slot_source": self._slot_source_map(
                slots=slots,
                explicit_slots=explicit_slots,
                inherited_slots=inherited_slots,
                corrected_slots=corrected_slots,
                time_source=time_window["source"],
                operation=follow_up.operation,
            ),
            "slot_confidence": self._slot_confidence_map(
                slots=slots,
                entity_confidence=resolved.entity_confidence,
                time_confidence=resolved.time_confidence,
            ),
            "operation": follow_up.operation,
            "parent_target_key": (latest_target or {}).get("target_key"),
            "selected_ref": follow_up.selected_ref,
            "rejected_candidates": follow_up.rejected_candidates,
        }
        logger.info(
            "follow-up resolution session_context_version=%s turn_id=%s operation=%s chosen_target_key=%s inherited_slots=%s clarify_reason=%s rejected_candidates=%s",
            current_context.get("context_version"),
            turn_id,
            follow_up.operation,
            context_meta["parent_target_key"],
            sorted(inherited_slots),
            follow_up.clarify_reason,
            context_meta["rejected_candidates"],
        )
        return resolved.resolved_args, time_window, resolved_entities, context_meta

    @staticmethod
    def _query_filters_from_args(resolved_args: dict[str, Any]) -> dict[str, Any]:
        return {
            "city": resolved_args.get("city"),
            "county": resolved_args.get("county"),
            "sn": resolved_args.get("sn"),
            "start_time": resolved_args.get("start_time"),
            "end_time": resolved_args.get("end_time"),
        }

    async def _query_records(self, resolved_args: dict[str, Any]) -> list[dict[str, Any]]:
        return await self.repository.filter_records_async(**self._query_filters_from_args(resolved_args))

    @staticmethod
    def _raw_row(row: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in row.items() if key in RAW_SOIL_KEYS}

    @staticmethod
    def _focus_device_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        latest_by_sn: dict[str, dict[str, Any]] = {}
        for record in records:
            sn = str(record.get("sn") or "")
            if not sn:
                continue
            create_time = str(record.get("create_time") or "")
            current = latest_by_sn.get(sn)
            if current is None or create_time > str(current.get("create_time") or "") or (
                create_time == str(current.get("create_time") or "") and sn < str(current.get("sn") or "")
            ):
                latest_by_sn[sn] = record
        rows = []
        for record in latest_by_sn.values():
            rows.append(
                {
                    "city": record.get("city"),
                    "county": record.get("county"),
                    "sn": record.get("sn"),
                    "create_time": record.get("create_time"),
                    "water20cm": record.get("water20cm"),
                    "t20cm": record.get("t20cm"),
                }
            )
        rows.sort(key=lambda item: str(item.get("sn") or ""))
        rows.sort(key=lambda item: str(item.get("create_time") or ""), reverse=True)
        return rows

    @staticmethod
    def _alert_record_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for record in records:
            rows.append(
                {
                    "city": record.get("city"),
                    "county": record.get("county"),
                    "sn": record.get("sn"),
                    "create_time": record.get("create_time"),
                    "water20cm": record.get("water20cm"),
                    "t20cm": record.get("t20cm"),
                }
            )
        rows.sort(key=lambda item: str(item.get("sn") or ""))
        rows.sort(key=lambda item: str(item.get("create_time") or ""), reverse=True)
        return rows

    @staticmethod
    def _top_regions_from_focus_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for row in rows:
            key = (row.get("city"), row.get("county"))
            bucket = grouped.setdefault(
                key,
                {
                    "city": row.get("city"),
                    "county": row.get("county"),
                    "device_keys": set(),
                    "record_count": 0,
                    "create_time": row.get("create_time"),
                    "water_values": [],
                },
            )
            sn = str(row.get("sn") or "").strip()
            if sn:
                bucket["device_keys"].add(sn)
            bucket["record_count"] += 1
            bucket["create_time"] = max(
                str(bucket.get("create_time") or ""),
                str(row.get("create_time") or ""),
            )
            water20 = _safe_float(row.get("water20cm"))
            if water20 is not None:
                bucket["water_values"].append(water20)
        result = []
        for bucket in grouped.values():
            bucket.pop("device_keys")
            bucket.pop("water_values")
            result.append(
                {
                    "city": bucket.get("city"),
                    "county": bucket.get("county"),
                }
            )
        result.sort(
            key=lambda item: (
                str(item.get("county") or ""),
                str(item.get("city") or ""),
            )
        )
        return result[:5]

    @staticmethod
    def _summary_metrics(records: list[dict[str, Any]], focus_rows: list[dict[str, Any]]) -> dict[str, Any]:
        water_values = [_safe_float(record.get("water20cm")) for record in records]
        valid_water = [value for value in water_values if value is not None]
        region_keys = {
            (record.get("city"), record.get("county"))
            for record in records
            if record.get("city") or record.get("county")
        }
        latest_create_time = max((str(record.get("create_time") or "") for record in records), default=None)
        return {
            "record_count": len(records),
            "device_count": len(focus_rows),
            "region_count": len(region_keys),
            "avg_water20cm": round(sum(valid_water) / len(valid_water), 2) if valid_water else None,
            "latest_create_time": latest_create_time,
        }

    async def _create_focus_snapshot(
        self,
        *,
        session_id: str,
        turn_id: int,
        block_id: str,
        query_spec: dict[str, Any],
        rule_version: str | None,
        rows: list[dict[str, Any]],
        snapshot_kind: str = "focus_devices",
    ) -> dict[str, Any]:
        try:
            return await self.snapshot_repository.create_snapshot_async(
                session_id=session_id,
                source_turn_id=turn_id,
                source_block_id=block_id,
                snapshot_kind=snapshot_kind,
                query_spec=query_spec,
                rule_version=rule_version,
                rows=rows,
            )
        except Exception as exc:
            raise DatabaseQueryError(f"结果快照写入失败：{exc}") from exc

    async def _maybe_create_companion_device_snapshot(
        self,
        *,
        session_id: str,
        turn_id: int,
        block_id: str,
        list_target: str,
        base_query_spec: dict[str, Any],
        source_snapshot_id: str | None,
        rows: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        if list_target != LIST_TARGET_ALERT_RECORDS:
            return None, []
        device_rows = self._focus_device_rows(rows)
        device_query_spec = {
            **base_query_spec,
            "grain": "device_list",
            "filters": {
                **(base_query_spec.get("filters") or {}),
                "source_snapshot_id": source_snapshot_id,
            },
            "sort": {"field": "create_time", "direction": "desc"},
        }
        snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec=device_query_spec,
            rule_version=None,
            rows=device_rows,
            snapshot_kind=LIST_TARGET_FOCUS_DEVICES,
        )
        return snapshot, device_rows

    @staticmethod
    def _resolved_args_from_context(current_context: dict[str, Any]) -> dict[str, Any] | None:
        primary_query_spec = current_context.get("primary_query_spec") or {}
        time_window = current_context.get("time_window") or primary_query_spec.get("time_window") or {}
        start_time = time_window.get("start_time")
        end_time = time_window.get("end_time")
        if not start_time or not end_time:
            return None

        entities = primary_query_spec.get("entities") or {}
        city = next(iter(entities.get("city") or []), None)
        county = next(iter(entities.get("county") or []), None)
        sn = next(iter(entities.get("sn") or []), None)

        if not city and not county and not sn:
            for entity in current_context.get("resolved_entities") or []:
                if entity.get("kind") == "city" and not city:
                    city = entity.get("canonical_name")
                elif entity.get("kind") == "county" and not county:
                    county = entity.get("canonical_name")
                elif entity.get("kind") == "device" and not sn:
                    sn = entity.get("canonical_name")

        return {
            "city": city,
            "county": county,
            "sn": sn,
            "start_time": start_time,
            "end_time": end_time,
        }

    async def _recover_snapshot_from_context(
        self,
        *,
        session_id: str,
        turn_id: int,
        block_id: str,
        current_context: dict[str, Any],
        snapshot_config: dict[str, Any],
    ) -> tuple[dict[str, Any], str] | tuple[None, None]:
        primary_query_spec = current_context.get("primary_query_spec") or {}
        if ((primary_query_spec.get("filters") or {}).get("source_snapshot_id")):
            return None, None

        resolved_args = self._resolved_args_from_context(current_context)
        if not resolved_args:
            return None, None

        records = await self._query_records(resolved_args)
        rows = self._alert_record_rows(records) if snapshot_config["grain"] == "record_list" else self._focus_device_rows(records)
        if not rows:
            return None, None

        snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec={
                **primary_query_spec,
                "capability": "list",
                "grain": snapshot_config["grain"],
                "filters": {
                    **((primary_query_spec.get("filters") or {})),
                    "source_snapshot_id": None,
                },
                "page": {"page": 1, "page_size": 50},
            },
            rule_version=None,
            rows=rows,
            snapshot_kind=snapshot_config["snapshot_kind"],
        )
        audit_sql = self.repository.build_filter_records_audit_sql(**self._query_filters_from_args(resolved_args))
        return snapshot, audit_sql

    async def _reply_summary(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            resolved_args, time_window, resolved_entities, resolution_meta = await self._resolve_filters(
                message=message,
                tool_name="query_soil_summary",
                current_context=current_context,
                turn_id=turn_id,
            )
        except ValueError as exc:
            return await self._build_filter_clarification_response(
                message=message,
                turn_id=turn_id,
                current_context=current_context,
                capability="summary",
                grain="aggregate",
                clarify_text=str(exc),
            )
        records = await self._query_records(resolved_args)
        if not records:
            return self._build_fallback_response(
                turn_id=turn_id,
                capability="summary",
                text="当前条件下没有查到墒情数据，你可以换一个地区、设备或扩大时间范围再试。",
                current_context=current_context,
            )

        block_id = f"block_summary_{turn_id}"
        device_rows = self._focus_device_rows(records)
        record_rows = self._alert_record_rows(records)
        metrics = self._summary_metrics(records, device_rows)
        query_spec = self._build_query_spec(
            capability="summary",
            grain="aggregate",
            time_window=time_window,
            resolved_args=resolved_args,
            source_turn_id=turn_id,
            follow_up_mode=self._follow_up_mode_from_operation(resolution_meta["operation"]),
        )
        device_snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec={**query_spec, "capability": "list", "grain": "device_list"},
            rule_version=None,
            rows=device_rows,
        )
        record_snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec={**query_spec, "capability": "list", "grain": "record_list"},
            rule_version=None,
            rows=record_rows,
            snapshot_kind=LIST_TARGET_ALERT_RECORDS,
        )
        top_regions = self._top_regions_from_focus_rows(record_rows)
        label = self._entity_label(resolved_entities) or "当前整体墒情"
        summary_text = self._render_summary_text(
            label=label,
            time_window=time_window,
            metrics=metrics,
            entity_confidence=resolution_meta["entity_confidence"],
            resolved_entities=resolved_entities,
        )
        block = {
            "block_id": block_id,
            "block_type": "summary_card",
            "display_mode": "evidence_only",
            "title": label,
            "time_window": time_window,
            "metrics": metrics,
            "top_regions": top_regions,
            "device_snapshot_id": device_snapshot["snapshot_id"],
            "record_snapshot_id": record_snapshot["snapshot_id"],
        }
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "time_window": time_window,
            "resolved_entities": resolved_entities,
            "derived_sets": {
                "device_snapshot_id": device_snapshot["snapshot_id"],
                "record_snapshot_id": record_snapshot["snapshot_id"],
                "region_group_snapshot_id": None,
            },
            "compare_winner_entity": None,
            "closed": False,
        }
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="summary",
            grain="aggregate",
            slots=resolution_meta["slots"],
            time_window=time_window,
            slot_confidence=resolution_meta["slot_confidence"],
            slot_source=resolution_meta["slot_source"],
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=resolution_meta["parent_target_key"],
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            action_targets=self._build_summary_action_targets(turn_id=turn_id, block=block),
            replace_history=resolution_meta["operation"] == "correct_slot",
        )
        executed_result = {
            "time_window": time_window,
            "metrics": metrics,
            "top_regions": top_regions,
            "device_snapshot_id": device_snapshot["snapshot_id"],
            "record_snapshot_id": record_snapshot["snapshot_id"],
        }
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "summary",
            "final_text": summary_text,
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {"has_query": True, "snapshot_ids": [device_snapshot["snapshot_id"], record_snapshot["snapshot_id"]]},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="summary",
                    query_spec=query_spec,
                    executed_sql_text=self.repository.build_filter_records_audit_sql(**self._query_filters_from_args(resolved_args)),
                    row_count=len(records),
                    snapshot_id=device_snapshot["snapshot_id"],
                    time_window=time_window,
                    filters=query_spec["filters"],
                    executed_result=executed_result,
                    result_digest={"metrics": metrics},
                )
            ],
        }

    async def _reply_list(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
        list_target: str,
        resolved_snapshot_id: str | None = None,
        resolved_snapshot_kind: str | None = None,
    ) -> dict[str, Any]:
        if current_context.get("topic_family") != "data":
            return self._build_guidance_response(
                turn_id=turn_id,
                text="当前没有可继承的数据查询上下文，请先查询一轮墒情数据，再追问这些点位。",
                current_context=current_context,
                guidance_reason="clarification",
            )

        snapshot_config = self._list_snapshot_config(list_target)
        block_id = f"block_list_{turn_id}"
        source_snapshot_id = resolved_snapshot_id or current_context.get("derived_sets", {}).get(snapshot_config["snapshot_key"])
        source_sql = None
        snapshot = None
        if source_snapshot_id:
            snapshot = await self.snapshot_repository.get_snapshot_async(source_snapshot_id)
        if not snapshot:
            snapshot, source_sql = await self._recover_snapshot_from_context(
                session_id=session_id,
                turn_id=turn_id,
                block_id=block_id,
                current_context=current_context,
                snapshot_config=snapshot_config,
            )
            source_snapshot_id = snapshot["snapshot_id"] if snapshot else None
        if not source_snapshot_id:
            return self._build_guidance_response(
                turn_id=turn_id,
                text=f"当前没有可继承的{snapshot_config['label']}上下文，请先查询一轮墒情数据后再继续追问。",
                current_context=current_context,
                guidance_reason="clarification",
            )
        if not snapshot:
            return self._build_guidance_response(
                turn_id=turn_id,
                text="当前会话的结果快照已失效，请重新发起一次数据查询。",
                current_context={**current_context, "closed": True},
                guidance_reason="clarification",
            )

        rows = [self._raw_row(item.get("payload_json") or {}) for item in snapshot.get("items") or []]
        follow_up_mode = "inherit"
        filter_entities = await self._extract_entities(message)
        if filter_entities["county"] or filter_entities["city"] or filter_entities["sn"]:
            rows = self._filter_snapshot_rows(rows, filter_entities)
            follow_up_mode = "subset"
        query_spec = {
            **(current_context.get("primary_query_spec") or {}),
            "capability": "list",
            "grain": snapshot_config["grain"],
            "page": {"page": 1, "page_size": LIST_TABLE_PAGE_SIZE},
            "filters": {
                **((current_context.get("primary_query_spec") or {}).get("filters") or {}),
                "source_snapshot_id": source_snapshot_id,
            },
            "sort": {"field": snapshot_config["sort_field"], "direction": "desc"},
            "provenance": {
                "source_turn_id": current_context.get("active_topic_turn_id") or turn_id,
                "follow_up_mode": follow_up_mode,
            },
        }
        next_snapshot_id = source_snapshot_id
        if follow_up_mode == "subset":
            next_snapshot = await self._create_focus_snapshot(
                session_id=session_id,
                turn_id=turn_id,
                block_id=block_id,
                query_spec=query_spec,
                rule_version=None,
                rows=rows,
                snapshot_kind=snapshot_config["snapshot_kind"],
            )
            next_snapshot_id = next_snapshot["snapshot_id"]
        device_snapshot = None
        device_rows: list[dict[str, Any]] = []
        if list_target == LIST_TARGET_ALERT_RECORDS:
            device_snapshot, device_rows = await self._maybe_create_companion_device_snapshot(
                session_id=session_id,
                turn_id=turn_id,
                block_id=block_id,
                list_target=list_target,
                base_query_spec=query_spec,
                source_snapshot_id=next_snapshot_id,
                rows=rows,
            )
        page_rows = rows[:LIST_TABLE_PAGE_SIZE]
        block = {
            "block_id": block_id,
            "block_type": "list_table",
            "title": snapshot_config["title"],
            "columns": snapshot_config["columns"],
            "rows": page_rows,
            "pagination": {
                "snapshot_id": next_snapshot_id,
                "page": 1,
                "page_size": LIST_TABLE_PAGE_SIZE,
                "total_count": len(rows),
                "total_pages": 0 if not rows else ((len(rows) - 1) // LIST_TABLE_PAGE_SIZE) + 1,
            },
        }
        resolved_entities = self._merge_context_entities(current_context, filter_entities)
        derived_sets = {
            **(current_context.get("derived_sets") or {}),
            snapshot_config["snapshot_key"]: next_snapshot_id,
        }
        if device_snapshot:
            derived_sets["device_snapshot_id"] = device_snapshot["snapshot_id"]
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "time_window": current_context.get("time_window") or {},
            "resolved_entities": resolved_entities,
            "derived_sets": derived_sets,
            "compare_winner_entity": current_context.get("compare_winner_entity"),
            "closed": False,
        }
        slots = self._slots_from_resolved_entities(resolved_entities)
        slot_confidence = self._slot_confidence_map(
            slots=slots,
            entity_confidence=CONFIDENCE_HIGH,
            time_confidence=CONFIDENCE_HIGH if current_context.get("time_window", {}).get("start_time") else "",
        )
        slot_source = self._slot_source_map(
            slots=slots,
            explicit_slots={
                key for key in ("province", "city", "county", "sn")
                if (filter_entities.get(key) or [])
            },
            inherited_slots={
                key for key, value in slots.items()
                if value and not (filter_entities.get(key) or [])
            },
            corrected_slots=set(),
            time_source=current_context.get("time_window", {}).get("source") or "",
            operation="subset" if follow_up_mode == "subset" else "inherit",
        )
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="list",
            grain=snapshot_config["grain"],
            slots=slots,
            time_window=current_context.get("time_window") or {},
            slot_confidence=slot_confidence,
            slot_source=slot_source,
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=(self._latest_follow_up_target(current_context) or {}).get("target_key"),
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            action_targets=self._build_list_action_targets(
                turn_id=turn_id,
                snapshot_id=next_snapshot_id,
                snapshot_kind=resolved_snapshot_kind or snapshot_config["snapshot_kind"],
                rows=rows,
                device_snapshot_id=device_snapshot["snapshot_id"] if device_snapshot else None,
                device_count=len(device_rows) if device_rows else None,
            ),
        )
        final_text = (
            f"已列出当前条件下的 {len(rows)} 条记录。"
            if list_target == LIST_TARGET_ALERT_RECORDS
            else f"已列出当前条件下的 {len(rows)} 个点位。"
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "list",
            "final_text": final_text,
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {
                "has_query": True,
                "snapshot_ids": [snapshot_id for snapshot_id in [next_snapshot_id, device_snapshot["snapshot_id"] if device_snapshot else None] if snapshot_id],
            },
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="list",
                    query_spec=query_spec,
                    executed_sql_text=source_sql or (
                        "SELECT payload_json FROM agent_result_snapshot_item "
                        f"WHERE snapshot_id = '{source_snapshot_id}' ORDER BY row_index ASC"
                    ),
                    row_count=len(rows),
                    snapshot_id=next_snapshot_id,
                    time_window=current_context.get("time_window") or {},
                    filters=query_spec["filters"],
                    executed_result={"rows": page_rows, "total_count": len(rows)},
                    result_digest={"total_count": len(rows)},
                )
            ],
        }

    async def _reply_standalone_list(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
        list_target: str,
    ) -> dict[str, Any]:
        snapshot_config = self._list_snapshot_config(list_target)
        try:
            resolved_args, time_window, resolved_entities, resolution_meta = await self._resolve_filters(
                message=message,
                tool_name="query_soil_summary",
                current_context=current_context,
                turn_id=turn_id,
            )
        except ValueError as exc:
            return await self._build_filter_clarification_response(
                message=message,
                turn_id=turn_id,
                current_context=current_context,
                capability="list",
                grain=snapshot_config["grain"],
                clarify_text=str(exc),
            )

        records = await self._query_records(resolved_args)
        if not records:
            return self._build_fallback_response(
                turn_id=turn_id,
                capability="list",
                text="当前条件下没有查到墒情数据，你可以换一个地区、设备或扩大时间范围再试。",
                current_context=current_context,
            )

        rows = self._alert_record_rows(records) if list_target == LIST_TARGET_ALERT_RECORDS else self._focus_device_rows(records)
        block_id = f"block_list_{turn_id}"
        query_spec = self._build_query_spec(
            capability="list",
            grain=snapshot_config["grain"],
            time_window=time_window,
            resolved_args=resolved_args,
            source_turn_id=turn_id,
            follow_up_mode=self._follow_up_mode_from_operation(resolution_meta["operation"]),
        )
        snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec=query_spec,
            rule_version=None,
            rows=rows,
            snapshot_kind=snapshot_config["snapshot_kind"],
        )
        device_snapshot = None
        device_rows: list[dict[str, Any]] = []
        if list_target == LIST_TARGET_ALERT_RECORDS:
            device_snapshot, device_rows = await self._maybe_create_companion_device_snapshot(
                session_id=session_id,
                turn_id=turn_id,
                block_id=block_id,
                list_target=list_target,
                base_query_spec=query_spec,
                source_snapshot_id=snapshot["snapshot_id"],
                rows=rows,
            )
        block = {
            "block_id": block_id,
            "block_type": "list_table",
            "title": snapshot_config["title"],
            "columns": snapshot_config["columns"],
            "rows": rows[:LIST_TABLE_PAGE_SIZE],
            "pagination": {
                "snapshot_id": snapshot["snapshot_id"],
                "page": 1,
                "page_size": LIST_TABLE_PAGE_SIZE,
                "total_count": len(rows),
                "total_pages": 0 if not rows else ((len(rows) - 1) // LIST_TABLE_PAGE_SIZE) + 1,
            },
        }
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "time_window": time_window,
            "resolved_entities": resolved_entities,
            "derived_sets": {
                snapshot_config["snapshot_key"]: snapshot["snapshot_id"],
                **({"device_snapshot_id": device_snapshot["snapshot_id"]} if device_snapshot else {}),
            },
            "compare_winner_entity": None,
            "closed": False,
        }
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="list",
            grain=snapshot_config["grain"],
            slots=resolution_meta["slots"],
            time_window=time_window,
            slot_confidence=resolution_meta["slot_confidence"],
            slot_source=resolution_meta["slot_source"],
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=resolution_meta["parent_target_key"],
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            action_targets=self._build_list_action_targets(
                turn_id=turn_id,
                snapshot_id=snapshot["snapshot_id"],
                snapshot_kind=snapshot_config["snapshot_kind"],
                rows=rows,
                device_snapshot_id=device_snapshot["snapshot_id"] if device_snapshot else None,
                device_count=len(device_rows) if device_rows else None,
            ),
            replace_history=resolution_meta["operation"] == "correct_slot",
        )
        final_text = (
            f"已列出当前条件下的 {len(rows)} 条记录。"
            if list_target == LIST_TARGET_ALERT_RECORDS
            else f"已列出当前条件下的 {len(rows)} 个点位。"
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "list",
            "final_text": final_text,
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {
                "has_query": True,
                "snapshot_ids": [
                    snapshot_id
                    for snapshot_id in [snapshot["snapshot_id"], device_snapshot["snapshot_id"] if device_snapshot else None]
                    if snapshot_id
                ],
            },
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="list",
                    query_spec=query_spec,
                    executed_sql_text=self.repository.build_filter_records_audit_sql(**self._query_filters_from_args(resolved_args)),
                    row_count=len(rows),
                    snapshot_id=snapshot["snapshot_id"],
                    time_window=time_window,
                    filters=query_spec["filters"],
                    executed_result={"rows": rows[:LIST_TABLE_PAGE_SIZE], "total_count": len(rows)},
                    result_digest={"total_count": len(rows)},
                )
            ],
        }

    async def _reply_group(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
        resolved_snapshot_id: str | None = None,
        resolved_snapshot_kind: str | None = None,
        resolved_group_by: str | None = None,
    ) -> dict[str, Any]:
        if current_context.get("topic_family") != "data":
            if not await self._can_run_standalone_group_query(message):
                return self._build_guidance_response(
                    turn_id=turn_id,
                    text="这轮还缺少明确的墒情查询条件，请直接补充时间范围、地区，或说明要按地区汇总，例如：最近30天按地区汇总墒情数据。",
                current_context=current_context,
                guidance_reason="clarification",
            )
            return await self._reply_standalone_group(
                message=message,
                session_id=session_id,
                turn_id=turn_id,
                current_context=current_context,
                resolved_group_by=resolved_group_by,
            )
        if await self._should_treat_group_request_as_standalone(text=message, current_context=current_context):
            return await self._reply_standalone_group(
                message=message,
                session_id=session_id,
                turn_id=turn_id,
                current_context=current_context,
                resolved_group_by=resolved_group_by,
            )

        del resolved_snapshot_kind
        snapshot_id = resolved_snapshot_id or current_context.get("derived_sets", {}).get(self._group_source_snapshot_key(current_context))
        snapshot = await self.snapshot_repository.get_snapshot_async(snapshot_id) if snapshot_id else None
        if not snapshot:
            return self._build_guidance_response(
                turn_id=turn_id,
                text="当前会话的结果快照已失效，请重新发起一次数据查询。",
                current_context=current_context,
                guidance_reason="clarification",
            )

        group_by = resolved_group_by or self._resolve_group_by(message)
        rows = self._group_rows(
            [self._raw_row(item.get("payload_json") or {}) for item in snapshot.get("items") or []],
            group_by=group_by,
        )
        block_id = f"block_group_{turn_id}"
        query_spec = {
            **(current_context.get("primary_query_spec") or {}),
            "capability": "group",
            "grain": "region_group" if group_by in {"county", "region"} else "aggregate",
            "filters": {
                **((current_context.get("primary_query_spec") or {}).get("filters") or {}),
                "source_snapshot_id": snapshot_id,
            },
            "provenance": {
                "source_turn_id": current_context.get("active_topic_turn_id") or turn_id,
                "follow_up_mode": "subset",
            },
        }
        block = {
            "block_id": block_id,
            "block_type": "group_table",
            "title": "地区汇总" if group_by == "region" else f"{self._group_label(group_by)}汇总",
            "group_by": group_by,
            "columns": REGION_GROUP_COLUMNS if group_by in {"region", "county"} else CITY_GROUP_COLUMNS,
            "rows": rows,
        }
        base_context = {
            **current_context,
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "closed": False,
        }
        slots = self._slots_from_context(current_context)
        slot_confidence = dict((current_context.get("query_state") or {}).get("slot_confidence") or {})
        slot_source = dict((current_context.get("query_state") or {}).get("slot_source") or {})
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="group",
            grain=query_spec["grain"],
            slots=slots,
            time_window=current_context.get("time_window") or {},
            slot_confidence=slot_confidence or self._slot_confidence_map(
                slots=slots,
                entity_confidence=CONFIDENCE_HIGH,
                time_confidence=CONFIDENCE_HIGH if current_context.get("time_window", {}).get("start_time") else "",
            ),
            slot_source=slot_source or self._slot_source_map(
                slots=slots,
                explicit_slots={key for key, value in slots.items() if value},
                inherited_slots=set(),
                corrected_slots=set(),
                time_source=current_context.get("time_window", {}).get("source") or "",
                operation="inherit",
            ),
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=(self._latest_follow_up_target(current_context) or {}).get("target_key"),
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            action_targets=[],
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "group",
            "final_text": f"已按{self._group_label(group_by)}完成汇总，共 {len(rows)} 组。",
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {"has_query": True, "snapshot_ids": [snapshot_id]},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="group",
                    query_spec=query_spec,
                    executed_sql_text=(
                        "SELECT payload_json FROM agent_result_snapshot_item "
                        f"WHERE snapshot_id = '{snapshot_id}' ORDER BY row_index ASC"
                    ),
                    row_count=len(rows),
                    snapshot_id=snapshot_id,
                    time_window=current_context.get("time_window") or {},
                    filters=query_spec["filters"],
                    executed_result={"rows": rows, "group_by": group_by},
                    result_digest={"group_count": len(rows)},
                )
            ],
        }

    async def _reply_standalone_group(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
        resolved_group_by: str | None = None,
    ) -> dict[str, Any]:
        try:
            resolved_args, time_window, resolved_entities, resolution_meta = await self._resolve_filters(
                message=message,
                tool_name="query_soil_group",
                current_context=current_context,
                allow_inherit_entities=False,
                turn_id=turn_id,
            )
        except ValueError as exc:
            return await self._build_filter_clarification_response(
                message=message,
                turn_id=turn_id,
                current_context=current_context,
                capability="group",
                grain="region_group",
                clarify_text=str(exc),
            )
        records = await self._query_records(resolved_args)
        if not records:
            return self._build_fallback_response(
                turn_id=turn_id,
                capability="group",
                text="当前条件下没有查到墒情数据，你可以换一个地区、设备或扩大时间范围再试。",
                current_context=current_context,
            )

        group_by = resolved_group_by or self._resolve_group_by(message)
        block_id = f"block_group_{turn_id}"
        device_rows = self._focus_device_rows(records)
        record_rows = self._alert_record_rows(records)
        rows = self._group_rows(record_rows, group_by=group_by)
        query_spec = self._build_query_spec(
            capability="group",
            grain="region_group" if group_by in {"county", "region"} else "aggregate",
            time_window=time_window,
            resolved_args=resolved_args,
            source_turn_id=turn_id,
            follow_up_mode=self._follow_up_mode_from_operation(resolution_meta["operation"]),
        )
        device_snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec={**query_spec, "capability": "list", "grain": "device_list"},
            rule_version=None,
            rows=device_rows,
        )
        record_snapshot = await self._create_focus_snapshot(
            session_id=session_id,
            turn_id=turn_id,
            block_id=block_id,
            query_spec={**query_spec, "capability": "list", "grain": "record_list"},
            rule_version=None,
            rows=record_rows,
            snapshot_kind=LIST_TARGET_ALERT_RECORDS,
        )
        block = {
            "block_id": block_id,
            "block_type": "group_table",
            "title": "地区汇总" if group_by == "region" else f"{self._group_label(group_by)}汇总",
            "group_by": group_by,
            "columns": REGION_GROUP_COLUMNS if group_by in {"region", "county"} else CITY_GROUP_COLUMNS,
            "rows": rows,
        }
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "time_window": time_window,
            "resolved_entities": resolved_entities,
            "derived_sets": {
                "device_snapshot_id": device_snapshot["snapshot_id"],
                "record_snapshot_id": record_snapshot["snapshot_id"],
                "region_group_snapshot_id": None,
            },
            "compare_winner_entity": None,
            "closed": False,
        }
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="group",
            grain=query_spec["grain"],
            slots=resolution_meta["slots"],
            time_window=time_window,
            slot_confidence=resolution_meta["slot_confidence"],
            slot_source=resolution_meta["slot_source"],
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=resolution_meta["parent_target_key"],
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            action_targets=[],
            replace_history=resolution_meta["operation"] == "correct_slot",
        )
        label = self._entity_label(resolved_entities) or "当前查询范围"
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "group",
            "final_text": (
                f"{label}{time_window['start_time'][:10]}至{time_window['end_time'][:10]}"
                f"已按{self._group_label(group_by)}汇总，共 {len(rows)} 组。"
            ),
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {
                "has_query": True,
                "snapshot_ids": [device_snapshot["snapshot_id"], record_snapshot["snapshot_id"]],
            },
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="group",
                    query_spec=query_spec,
                    executed_sql_text=self.repository.build_filter_records_audit_sql(
                        **self._query_filters_from_args(resolved_args)
                    ),
                    row_count=len(records),
                    snapshot_id=device_snapshot["snapshot_id"],
                    time_window=time_window,
                    filters=query_spec["filters"],
                    executed_result={"rows": rows, "group_by": group_by},
                    result_digest={"group_count": len(rows)},
                )
            ],
        }

    @staticmethod
    def _resolve_group_by(message: str) -> str:
        if "地区" in message or "区域" in message:
            return "region"
        if "县" in message or "区" in message:
            return "county"
        if "市" in message:
            return "city"
        return "region"

    @staticmethod
    def _group_key_for_row(row: dict[str, Any], group_by: str) -> str:
        if group_by == "region":
            city = str(row.get("city") or "").strip()
            county = str(row.get("county") or "").strip()
            if city and county:
                return f"{city}-{county}"
            return city or county or "未知"
        if group_by == "county":
            return str(row.get("county") or row.get("city") or "未知")
        if group_by == "city":
            return str(row.get("city") or "未知")
        return str(row.get(group_by) or "未知")

    @staticmethod
    def _group_label(group_by: str) -> str:
        if group_by == "region":
            return "地区"
        if group_by == "county":
            return "县区"
        if group_by == "city":
            return "城市"
        return "分组"

    @staticmethod
    def _group_rows(rows: list[dict[str, Any]], *, group_by: str) -> list[dict[str, Any]]:
        grouped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for row in rows:
            city = str(row.get("city") or "").strip() or None
            county = str(row.get("county") or "").strip() or None
            if group_by == "city":
                key = (city, None)
                payload = {"city": city}
            elif group_by == "county":
                key = (city, county)
                payload = {"city": city, "county": county}
            else:
                key = (city, county)
                payload = {"city": city, "county": county}
            if not any(key):
                continue
            grouped.setdefault(key, payload)
        grouped_rows = list(grouped.values())
        grouped_rows.sort(
            key=lambda item: (
                str(item.get("county") or ""),
                str(item.get("city") or ""),
            )
        )
        return grouped_rows

    async def _reply_detail(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            resolved_args, time_window, resolved_entities, resolution_meta = await self._resolve_filters(
                message=message,
                tool_name="query_soil_detail",
                current_context=current_context,
                turn_id=turn_id,
            )
        except ValueError as exc:
            return await self._build_filter_clarification_response(
                message=message,
                turn_id=turn_id,
                current_context=current_context,
                capability="detail",
                grain="entity_detail",
                clarify_text=str(exc),
            )
        records = await self._query_records(resolved_args)
        if not records:
            return self._build_fallback_response(
                turn_id=turn_id,
                capability="detail",
                text="当前条件下没有查到对应的详情数据，你可以换一个地区、设备或扩大时间范围再试。",
                current_context=current_context,
            )
        latest_record = self._raw_row(records[0])
        focus_rows = self._focus_device_rows(records)
        metrics = self._summary_metrics(records, focus_rows)
        block_id = f"block_detail_{turn_id}"
        label = self._entity_label(resolved_entities) or str(latest_record.get("sn") or "详情")
        query_spec = self._build_query_spec(
            capability="detail",
            grain="entity_detail",
            time_window=time_window,
            resolved_args=resolved_args,
            source_turn_id=turn_id,
            follow_up_mode=self._follow_up_mode_from_operation(resolution_meta["operation"]),
        )
        block = {
            "block_id": block_id,
            "block_type": "detail_card",
            "display_mode": "evidence_only",
            "title": label,
            "time_window": time_window,
            "metrics": metrics,
            "latest_record": latest_record,
        }
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "time_window": time_window,
            "resolved_entities": resolved_entities,
            "derived_sets": {
                "device_snapshot_id": None,
                "record_snapshot_id": None,
                "region_group_snapshot_id": None,
            },
            "compare_winner_entity": None,
            "closed": False,
        }
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="detail",
            grain="entity_detail",
            slots=resolution_meta["slots"],
            time_window=time_window,
            slot_confidence=resolution_meta["slot_confidence"],
            slot_source=resolution_meta["slot_source"],
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=resolution_meta["parent_target_key"],
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            replace_history=resolution_meta["operation"] == "correct_slot",
        )
        final_text = self._render_detail_text(
            label,
            time_window,
            latest_record,
            resolution_meta["entity_confidence"],
            resolved_entities,
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "detail",
            "final_text": final_text,
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {"has_query": True, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="detail",
                    query_spec=query_spec,
                    executed_sql_text=self.repository.build_filter_records_audit_sql(**self._query_filters_from_args(resolved_args)),
                    row_count=len(records),
                    snapshot_id=None,
                    time_window=time_window,
                    filters=query_spec["filters"],
                    executed_result={"latest_record": latest_record, "metrics": metrics},
                    result_digest={"latest_sn": latest_record.get("sn")},
                )
            ],
        }

    async def _reply_compare(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        latest_business_time = await self._latest_business_time()
        time_evidence = self.time_window_service.resolve(message, latest_business_time)
        base_resolved = await self.parameter_resolver.resolve(
            tool_name="query_soil_summary",
            raw_args={},
            latest_business_time=latest_business_time,
            user_input=message,
            time_evidence=time_evidence,
            inherited_time_window=(current_context.get("time_window") or None) if current_context.get("topic_family") == "data" else None,
        )
        time_window = {
            "start_time": base_resolved.resolved_args["start_time"],
            "end_time": base_resolved.resolved_args["end_time"],
            "source": base_resolved.time_source or "default_recent_7d",
        }
        entities = await self._extract_entities(message)
        names = []
        for item in entities["resolved"]:
            canonical_name = item["canonical_name"]
            if canonical_name not in names:
                names.append(canonical_name)
        if len(names) < 2:
            return self._build_guidance_response(
                turn_id=turn_id,
                text="对比查询至少需要两个地区或设备，例如：南通和盐城最近哪边更差。",
                current_context=current_context,
                guidance_reason="clarification",
            )

        compared = []
        for name in names[:2]:
            filters = {
                "city": name if name.endswith("市") else None,
                "county": name if name.endswith(("县", "区")) else None,
                "sn": name if name.startswith("SNS") else None,
                "start_time": time_window["start_time"],
                "end_time": time_window["end_time"],
            }
            records = await self.repository.filter_records_async(**filters)
            focus_rows = self._focus_device_rows(records)
            metrics = self._summary_metrics(records, focus_rows)
            compared.append(
                {
                    "entity": name,
                    "record_count": metrics["record_count"],
                    "device_count": metrics["device_count"],
                    "region_count": metrics["region_count"],
                    "avg_water20cm": metrics["avg_water20cm"],
                    "latest_create_time": metrics["latest_create_time"],
                }
            )
        block_id = f"block_compare_{turn_id}"
        query_spec = {
            "spec_id": f"qs_{turn_id}_compare",
            "dataset": "fact_soil_moisture",
            "capability": "compare",
            "grain": "entity_compare",
            "time_window": time_window,
            "entities": {"city": names, "county": [], "sn": []},
            "filters": {"source_snapshot_id": None},
            "sort": {"field": "entity", "direction": "asc"},
            "page": {"page": 1, "page_size": 50},
            "provenance": {"source_turn_id": turn_id, "follow_up_mode": "standalone"},
        }
        block = {
            "block_id": block_id,
            "block_type": "compare_card",
            "display_mode": "evidence_only",
            "title": "对比结果",
            "time_window": time_window,
            "rows": compared,
        }
        base_context = {
            "topic_family": "data",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": query_spec,
            "time_window": time_window,
            "resolved_entities": [{"kind": "city", "canonical_name": name} for name in names[:2]],
            "derived_sets": {},
            "compare_winner_entity": None,
            "closed": False,
        }
        slots = {"province": None, "city": None, "county": None, "sn": None}
        query_state = self._build_query_state(
            turn_id=turn_id,
            capability="compare",
            grain="entity_compare",
            slots=slots,
            time_window=time_window,
            slot_confidence=self._slot_confidence_map(
                slots=slots,
                entity_confidence=CONFIDENCE_HIGH,
                time_confidence=CONFIDENCE_HIGH,
            ),
            slot_source=self._slot_source_map(
                slots=slots,
                explicit_slots={key for key, value in slots.items() if value},
                inherited_slots=set(),
                corrected_slots=set(),
                time_source=time_window["source"],
                operation="standalone",
            ),
        )
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
            query_state=query_state,
            parent_target_key=(self._latest_follow_up_target(current_context) or {}).get("target_key"),
            result_refs=self._build_result_refs(turn_id=turn_id, block=block),
            action_targets=[],
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "compare",
            "final_text": f"已按相同时间范围整理 {names[0]} 和 {names[1]} 的原始统计对比，可继续查看其中一个对象的详情。",
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {"has_query": True, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="compare",
                    query_spec=query_spec,
                    executed_sql_text=";\n\n".join(
                        self.repository.build_filter_records_audit_sql(
                            city=name if name.endswith("市") else None,
                            county=name if name.endswith(("县", "区")) else None,
                            start_time=time_window["start_time"],
                            end_time=time_window["end_time"],
                        )
                        for name in names[:2]
                    ),
                    row_count=sum(int(item["record_count"]) for item in compared),
                    snapshot_id=None,
                    time_window=time_window,
                    filters=query_spec["filters"],
                    executed_result={"rows": compared},
                    result_digest={"entities": names[:2]},
                )
            ],
        }

    async def _reply_rule(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        del message
        row = await self.repository.warning_rule_row_async()
        if not row:
            return self._build_fallback_response(
                turn_id=turn_id,
                capability="rule",
                text="当前规则不可用，请联系管理员检查配置。",
                current_context=current_context,
            )
        rule_definition = row.get("rule_definition_json")
        if isinstance(rule_definition, str):
            try:
                rule_definition = json.loads(rule_definition)
            except json.JSONDecodeError:
                rule_definition = {"raw": rule_definition}
        thresholds = {}
        for item in (rule_definition or {}).get("rules", []):
            condition = str(item.get("condition") or "")
            level = str(item.get("warning_level") or "")
            if level == "heavy_drought" and "<" in condition:
                thresholds["heavy_drought"] = condition
            elif level == "waterlogging" and ">=" in condition:
                thresholds["waterlogging"] = condition
            elif level == "device_fault":
                thresholds["device_fault"] = condition
        block_id = f"block_rule_{turn_id}"
        block = {
            "block_id": block_id,
            "block_type": "rule_card",
            "display_mode": "evidence_only",
            "rule_code": row.get("rule_code"),
            "rule_name": row.get("rule_name"),
            "updated_at": row.get("updated_at"),
            "thresholds": thresholds,
            "rule_definition_json": rule_definition,
        }
        base_context = {
            "topic_family": "rule",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": {},
            "time_window": {},
            "resolved_entities": [],
            "derived_sets": {},
            "compare_winner_entity": None,
            "closed": False,
        }
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "rule",
            "final_text": self._render_rule_text(row, thresholds),
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {"has_query": True, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="rule",
                    query_spec={
                        "spec_id": f"qs_{turn_id}_rule",
                        "dataset": "metric_rule",
                        "capability": "rule",
                        "grain": "rule_read",
                        "time_window": {},
                        "entities": {"city": [], "county": [], "sn": []},
                        "filters": {"alert_only": False, "status_in": [], "source_snapshot_id": None},
                        "sort": {"field": "updated_at", "direction": "desc"},
                        "page": {"page": 1, "page_size": 1},
                        "provenance": {"source_turn_id": turn_id, "follow_up_mode": "standalone"},
                    },
                    executed_sql_text=self.repository.build_warning_rule_audit_sql(),
                    row_count=1,
                    snapshot_id=None,
                    time_window={},
                    filters={"rule_code": row.get("rule_code")},
                    executed_result={"rule": row},
                    result_digest={"rule_code": row.get("rule_code"), "updated_at": row.get("updated_at")},
                )
            ],
        }

    async def _reply_template(
        self,
        *,
        message: str,
        session_id: str,
        turn_id: int,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        del message
        row = await self.repository.warning_template_row_async()
        if not row:
            return self._build_fallback_response(
                turn_id=turn_id,
                capability="template",
                text="当前模板不可用，请联系管理员检查配置。",
                current_context=current_context,
            )
        block_id = f"block_template_{turn_id}"
        block = {
            "block_id": block_id,
            "block_type": "template_card",
            "template_id": row.get("template_id"),
            "template_name": row.get("template_name"),
            "template_text": row.get("template_text"),
            "required_fields_json": row.get("required_fields_json"),
            "version": row.get("version"),
            "updated_at": row.get("updated_at"),
        }
        base_context = {
            "topic_family": "template",
            "active_topic_turn_id": turn_id,
            "primary_block_id": block_id,
            "primary_query_spec": {},
            "time_window": {},
            "resolved_entities": [],
            "derived_sets": {},
            "compare_winner_entity": None,
            "closed": False,
        }
        turn_context = self._finalize_context(
            base_context=base_context,
            current_context=current_context,
            turn_id=turn_id,
        )
        return {
            "turn_id": turn_id,
            "answer_kind": "business",
            "capability": "template",
            "final_text": f"当前启用的预警模板是《{row.get('template_name') or '未命名模板'}》，可直接用于墒情预警通知。",
            "blocks": [block],
            "topic": self._topic_payload(turn_context),
            "turn_context": turn_context,
            "query_ref": {"has_query": True, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [
                self._build_query_log_entry(
                    session_id=session_id,
                    turn_id=turn_id,
                    query_index=1,
                    query_type="template",
                    query_spec={
                        "spec_id": f"qs_{turn_id}_template",
                        "dataset": "warning_template",
                        "capability": "template",
                        "grain": "template_read",
                        "time_window": {},
                        "entities": {"city": [], "county": [], "sn": []},
                        "filters": {"alert_only": False, "status_in": [], "source_snapshot_id": None},
                        "sort": {"field": "updated_at", "direction": "desc"},
                        "page": {"page": 1, "page_size": 1},
                        "provenance": {"source_turn_id": turn_id, "follow_up_mode": "standalone"},
                    },
                    executed_sql_text=self.repository.build_warning_template_audit_sql(),
                    row_count=1,
                    snapshot_id=None,
                    time_window={},
                    filters={"template_id": row.get("template_id")},
                    executed_result={"template": row},
                    result_digest={"template_id": row.get("template_id"), "version": row.get("version")},
                )
            ],
        }

    def _build_fallback_response(
        self,
        *,
        turn_id: int,
        capability: str,
        text: str,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "turn_id": turn_id,
            "answer_kind": "fallback",
            "capability": capability,
            "final_text": text,
            "blocks": [
                {
                    "block_id": f"block_fallback_{turn_id}",
                    "block_type": "fallback_card",
                    "text": text,
                    "reason": "no_data",
                }
            ],
            "topic": self._topic_payload(current_context),
            "turn_context": current_context,
            "query_ref": {"has_query": False, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [],
        }

    @staticmethod
    def _merge_context_entities(current_context: dict[str, Any], filter_entities: dict[str, Any]) -> list[dict[str, Any]]:
        if filter_entities.get("province"):
            return [{"kind": "province", "canonical_name": filter_entities["province"][0]}]
        if filter_entities["sn"]:
            return [{"kind": "device", "canonical_name": filter_entities["sn"][0]}]
        if filter_entities["county"]:
            entities = []
            for entity in current_context.get("resolved_entities") or []:
                if entity.get("kind") == "city":
                    entities.append(entity)
                    break
            entities.append({"kind": "county", "canonical_name": filter_entities["county"][0]})
            return entities
        if filter_entities["city"]:
            return [{"kind": "city", "canonical_name": filter_entities["city"][0]}]
        return current_context.get("resolved_entities") or []

    @staticmethod
    def _list_snapshot_config(list_target: str) -> dict[str, Any]:
        if list_target == LIST_TARGET_ALERT_RECORDS:
            return {
                "snapshot_key": "record_snapshot_id",
                "snapshot_kind": LIST_TARGET_ALERT_RECORDS,
                "grain": "record_list",
                "title": "记录详情",
                "label": "记录",
                "columns": ALERT_RECORD_COLUMNS,
                "sort_field": "create_time",
            }
        return {
            "snapshot_key": "device_snapshot_id",
            "snapshot_kind": LIST_TARGET_FOCUS_DEVICES,
            "grain": "device_list",
            "title": "点位详情",
            "label": "点位",
            "columns": FOCUS_DEVICE_COLUMNS,
            "sort_field": "create_time",
        }

    def _group_source_snapshot_key(self, current_context: dict[str, Any]) -> str:
        if self._current_list_grain(current_context) == "record_list":
            return "record_snapshot_id"
        return "device_snapshot_id"

    @staticmethod
    def _follow_up_mode_from_operation(operation: str) -> str:
        if operation == "subset":
            return "subset"
        if operation == "drilldown_ref":
            return "drilldown"
        if operation in {"inherit", "replace_slot", "correct_slot", "switch_capability"}:
            return "inherit"
        return "standalone"

    @staticmethod
    def _filter_snapshot_rows(rows: list[dict[str, Any]], filter_entities: dict[str, Any]) -> list[dict[str, Any]]:
        city_values = {value for value in filter_entities.get("city") or []}
        county_values = {value for value in filter_entities.get("county") or []}
        sn_values = {value for value in filter_entities.get("sn") or []}
        filtered = []
        for row in rows:
            if city_values and row.get("city") not in city_values:
                continue
            if county_values and row.get("county") not in county_values:
                continue
            if sn_values and row.get("sn") not in sn_values:
                continue
            filtered.append(row)
        return filtered

    def _build_query_spec(
        self,
        *,
        capability: str,
        grain: str,
        time_window: dict[str, Any],
        resolved_args: dict[str, Any],
        source_turn_id: int,
        follow_up_mode: str,
    ) -> dict[str, Any]:
        return {
            "spec_id": f"qs_{source_turn_id}_{capability}",
            "dataset": "fact_soil_moisture",
            "capability": capability,
            "grain": grain,
            "time_window": time_window,
            "entities": {
                "city": [resolved_args["city"]] if resolved_args.get("city") else [],
                "county": [resolved_args["county"]] if resolved_args.get("county") else [],
                "sn": [resolved_args["sn"]] if resolved_args.get("sn") else [],
            },
            "filters": {"source_snapshot_id": None},
            "sort": {"field": "latest_create_time" if grain == "device_list" else "create_time", "direction": "desc"},
            "page": {"page": 1, "page_size": LIST_TABLE_PAGE_SIZE if capability == "list" else 50},
            "provenance": {
                "source_turn_id": source_turn_id,
                "follow_up_mode": follow_up_mode,
            },
        }

    def _build_partial_query_spec(
        self,
        *,
        capability: str,
        grain: str,
        source_turn_id: int,
        follow_up_mode: str,
        resolved_entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "spec_id": f"qs_{source_turn_id}_{capability}_clarify",
            "dataset": "fact_soil_moisture",
            "capability": capability,
            "grain": grain,
            "time_window": {},
            "entities": {
                "city": [item["canonical_name"] for item in resolved_entities if item.get("kind") == "city"],
                "county": [item["canonical_name"] for item in resolved_entities if item.get("kind") == "county"],
                "sn": [item["canonical_name"] for item in resolved_entities if item.get("kind") == "device"],
            },
            "filters": {"source_snapshot_id": None},
            "sort": {"field": "create_time", "direction": "desc"},
            "page": {"page": 1, "page_size": 50},
            "provenance": {
                "source_turn_id": source_turn_id,
                "follow_up_mode": follow_up_mode,
            },
        }

    @staticmethod
    def _entity_label(resolved_entities: list[dict[str, Any]]) -> str:
        if not resolved_entities:
            return ""
        ordered = [item.get("canonical_name") for item in resolved_entities if item.get("canonical_name")]
        return "".join(ordered)

    @staticmethod
    def _render_summary_text(
        *,
        label: str,
        time_window: dict[str, Any],
        metrics: dict[str, Any],
        entity_confidence: str,
        resolved_entities: list[dict[str, Any]],
    ) -> str:
        scope = label or "当前整体墒情"
        avg_text = "暂无" if metrics.get("avg_water20cm") is None else f"{metrics['avg_water20cm']}%"
        latest_time = str(metrics.get("latest_create_time") or "暂无")
        text = (
            f"{scope}{time_window['start_time'][:10]}至{time_window['end_time'][:10]}的墒情概况如下："
            f"20cm平均相对含水量约 {avg_text}，"
            f"共有 {metrics['record_count']} 条记录，涉及 {metrics['device_count']} 个点位，"
            f"覆盖 {metrics['region_count']} 个地区，最新记录时间为 {latest_time}。"
        )
        if entity_confidence == CONFIDENCE_MEDIUM and resolved_entities:
            text += f" 当前按近似匹配识别为 {resolved_entities[-1]['canonical_name']}，置信度中。"
        text += " 如需继续查看，可以直接回复：列出点位详情、列出记录详情，或按地区汇总。"
        return text

    @staticmethod
    def _render_detail_text(
        label: str,
        time_window: dict[str, Any],
        latest_record: dict[str, Any],
        entity_confidence: str,
        resolved_entities: list[dict[str, Any]],
    ) -> str:
        water20 = latest_record.get("water20cm")
        location = f"{latest_record.get('city') or ''}{latest_record.get('county') or ''}".strip()
        latest_time = str(latest_record.get("create_time") or latest_record.get("latest_create_time") or "暂无")
        text = (
            f"{label}{time_window['start_time'][:10]}至{time_window['end_time'][:10]}的最新详情如下："
            f"最近一条记录时间为 {latest_time}，"
            f"{f'位于 {location}，' if location else ''}"
            f"20cm含水量 {water20}%。"
        )
        if entity_confidence == CONFIDENCE_MEDIUM and resolved_entities:
            text += f" 当前按近似匹配识别为 {resolved_entities[-1]['canonical_name']}，置信度中。"
        return text

    @staticmethod
    def _render_rule_text(row: dict[str, Any], thresholds: dict[str, Any]) -> str:
        return (
            f"当前启用规则是《{row.get('rule_name') or row.get('rule_code') or '未命名规则'}》。"
            f"其中重旱条件为 {thresholds.get('heavy_drought', '未配置')}，"
            f"涝渍条件为 {thresholds.get('waterlogging', '未配置')}，"
            f"设备故障条件为 {thresholds.get('device_fault', '未配置')}。"
        )

    @staticmethod
    def _build_query_log_entry(
        *,
        session_id: str,
        turn_id: int,
        query_index: int,
        query_type: str,
        query_spec: dict[str, Any],
        executed_sql_text: str,
        row_count: int,
        snapshot_id: str | None,
        time_window: dict[str, Any],
        filters: dict[str, Any],
        executed_result: dict[str, Any],
        result_digest: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "query_id": f"{session_id}:{turn_id}:{query_index}",
            "session_id": session_id,
            "turn_id": turn_id,
            "query_type": query_type,
            "query_plan_json": {
                "capability": query_spec.get("capability"),
                "grain": query_spec.get("grain"),
            },
            "query_spec_json": query_spec,
            "sql_fingerprint": None,
            "executed_sql_text": executed_sql_text,
            "time_range_json": time_window,
            "filters_json": filters,
            "group_by_json": None,
            "metrics_json": None,
            "order_by_json": query_spec.get("sort"),
            "limit_size": (query_spec.get("page") or {}).get("page_size"),
            "row_count": row_count,
            "snapshot_id": snapshot_id,
            "executed_result_json": executed_result,
            "result_digest_json": result_digest,
            "source_files_json": None,
            "status": "succeeded",
            "error_message": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

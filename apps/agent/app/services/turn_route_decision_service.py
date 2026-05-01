"""Centralized top-level route decision for deterministic data-answer turns."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from app.services.query_profile_resolver_service import QueryProfileResolverService


SN_PATTERN = re.compile(r"SNS\d{8}", re.IGNORECASE)
LIST_TARGET_FOCUS_DEVICES = "devices"
LIST_TARGET_ALERT_RECORDS = "records"
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
QUERY_CUE_TOKENS = ("查", "看", "情况", "怎么样", "有没有问题", "需要", "最近", "最新")
DETAIL_HINT_TOKENS = ("详情", "明细")
LIST_ENUMERATION_TOKENS = ("哪些", "哪几个", "有哪些")
TEMPLATE_TOKENS = ("模板", "模版")
RANKING_MARKERS = ("最多", "最少", "最高", "最低", "排名", "排行", "top")
REGION_GROUP_REQUEST_PATTERNS = (
    re.compile(r"(覆盖|涉及).*(地方|地区|区域)"),
    re.compile(r"((?:有|又)?哪些|哪[0-9一二两三四五六七八九十百]*个).*(地方|地区|区域)"),
    re.compile(r"^[0-9一二两三四五六七八九十百]+\s*个?\s*(地方|地区|区域)(?:呢|详情|明细)?$"),
    re.compile(r"^(这些|这几个|那些|上面的)\s*(地方|地区|区域)(?:呢|详情|明细)?$"),
)
PLAIN_GROUP_FOLLOW_UP_PATTERN = re.compile(r"^(?:地区|地方|区域)(?:详情|明细)?(?:呢)?$")
TEXT_NORMALIZATION_RULES: tuple[tuple[str, str], ...] = (
    ("又哪些地方", "有哪些地方"),
    ("又哪些地区", "有哪些地区"),
    ("哪几个地方", "哪些地方"),
)


@dataclass(frozen=True)
class QueryShape:
    subject: str = "soil"
    action: str = "summary"
    grain: str = "none"
    mode: str = "standalone"


@dataclass(frozen=True)
class TurnRouteDecision:
    route: str
    list_target: str | None = None
    group_by: str | None = None
    normalized_text: str = ""
    route_source: str = "direct"
    query_shape: QueryShape = field(default_factory=QueryShape)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


class TurnRouteDecisionService:
    """Choose the single top-level route for one chat turn."""

    def decide(
        self,
        *,
        message: str,
        current_context: dict[str, Any] | None,
        entities: dict[str, Any] | None,
        time_evidence: Any | None,
        action_result: Any | None,
    ) -> TurnRouteDecision:
        context = current_context if isinstance(current_context, dict) else {}
        extracted_entities = entities if isinstance(entities, dict) else {}
        normalized_text = self._normalize_text(message)
        normalized_changed = normalized_text != str(message or "").strip()

        subject = self._classify_subject(normalized_text)
        if subject == "rule":
            return self._decision(
                route="rule",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="rule", action="guidance", grain="none", mode="standalone"),
                reason_codes=("rule_request",),
            )
        if subject == "template":
            return self._decision(
                route="template",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="template", action="guidance", grain="none", mode="standalone"),
                reason_codes=("template_request",),
            )
        if subject == "unsupported_derived":
            return self._decision(
                route="unsupported_derived",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="unsupported_derived", action="guidance", grain="none", mode="standalone"),
                reason_codes=("unsupported_derived",),
            )

        has_explicit_detail = self._has_explicit_detail(normalized_text, extracted_entities)
        is_group_request = self._is_group_request(normalized_text)
        is_plain_group_follow_up = self._is_plain_group_follow_up_phrase(normalized_text)
        group_by = self._resolve_group_by(normalized_text) if is_group_request else None
        list_target = None if is_group_request else self._resolve_list_target(normalized_text, context)
        is_compare_request = self._is_compare_request(normalized_text)
        is_latest_record_request = QueryProfileResolverService.is_latest_record_request(normalized_text)
        is_count_request = QueryProfileResolverService.is_count_request(normalized_text)
        is_field_request = QueryProfileResolverService.is_field_request(normalized_text)
        is_detail_request = self._is_detail_request(normalized_text, extracted_entities)
        should_follow_up_detail = self._should_follow_up_detail(
            text=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
            has_explicit_detail=has_explicit_detail,
            is_group_request=is_group_request,
            list_target=list_target,
            is_compare_request=is_compare_request,
        )
        should_group_standalone = is_group_request and self._should_treat_group_request_as_standalone(
            text=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
        )
        should_list_standalone = bool(list_target) and self._should_treat_list_request_as_standalone(
            text=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
        )
        should_safe_hint = self._should_return_safe_hint_before_summary(
            text=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
        )
        should_follow_up_count = self._should_follow_up_count(
            text=normalized_text,
            current_context=context,
            entities=extracted_entities,
            time_evidence=time_evidence,
            is_group_request=is_group_request,
            list_target=list_target,
            is_compare_request=is_compare_request,
        )
        action_operation = str(getattr(action_result, "operation", "") or "")

        if is_group_request and should_group_standalone:
            return self._decision(
                route="standalone_group",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                group_by=group_by or "region",
                query_shape=QueryShape(subject="soil", action="group", grain="region", mode="standalone"),
                reason_codes=("group_request", "standalone_signals"),
            )

        if list_target and should_list_standalone:
            return self._decision(
                route="standalone_list",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                list_target=list_target,
                query_shape=QueryShape(subject="soil", action="list", grain=self._grain_for_list_target(list_target), mode="standalone"),
                reason_codes=("list_request", "standalone_signals"),
            )

        if is_count_request:
            return self._decision(
                route="count",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(
                    subject="soil",
                    action="count",
                    grain=self._count_grain(normalized_text),
                    mode="standalone",
                ),
                reason_codes=("count_request",),
            )

        if is_field_request:
            return self._decision(
                route="field",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="soil", action="field", grain="entity", mode="standalone"),
                reason_codes=("field_request",),
            )

        if is_compare_request:
            return self._decision(
                route="compare",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="soil", action="compare", grain="entity", mode="standalone"),
                reason_codes=("compare_request",),
            )

        if is_latest_record_request:
            return self._decision(
                route="latest_record",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="soil", action="detail", grain="entity", mode="standalone"),
                reason_codes=("latest_record_request",),
            )

        if has_explicit_detail:
            return self._decision(
                route="explicit_detail",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="soil", action="detail", grain="entity", mode="explicit_detail"),
                reason_codes=("explicit_detail",),
            )

        if action_operation == "clarify" and not list_target and not is_plain_group_follow_up:
            return self._decision(
                route="follow_up_action_clarify",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                route_source="action_target",
                query_shape=QueryShape(subject="soil", action="guidance", grain="none", mode="action_target"),
                reason_codes=("action_target_clarify",),
            )

        if action_operation == "expand_target":
            selected_target = getattr(action_result, "selected_action_target", None) or {}
            action = self._query_action_from_target(selected_target, subject_kind=str(getattr(action_result, "subject_kind", "") or ""))
            return self._decision(
                route="follow_up_action_expand",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                route_source="action_target",
                list_target=self._list_target_from_action_target(selected_target),
                group_by=str(selected_target.get("group_by") or "") or None,
                query_shape=QueryShape(
                    subject="soil",
                    action=action,
                    grain=self._query_grain_from_target(
                        selected_target,
                        subject_kind=str(getattr(action_result, "subject_kind", "") or ""),
                    ),
                    mode="action_target",
                ),
                reason_codes=("action_target_expand",),
            )

        if list_target:
            return self._decision(
                route="follow_up_list",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                route_source="context",
                list_target=list_target,
                query_shape=QueryShape(subject="soil", action="list", grain=self._grain_for_list_target(list_target), mode="contextual"),
                reason_codes=("list_request", "context_follow_up"),
            )

        if is_group_request:
            return self._decision(
                route="follow_up_group",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                route_source="context",
                group_by=group_by or "region",
                query_shape=QueryShape(subject="soil", action="group", grain="region", mode="contextual"),
                reason_codes=("group_request", "context_follow_up"),
            )

        if should_follow_up_detail:
            return self._decision(
                route="follow_up_detail",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                route_source="context",
                query_shape=QueryShape(subject="soil", action="detail", grain="entity", mode="contextual"),
                reason_codes=("detail_context", "context_follow_up"),
            )

        if should_follow_up_count:
            return self._decision(
                route="count",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                route_source="context",
                query_shape=QueryShape(subject="soil", action="count", grain="entity", mode="contextual"),
                reason_codes=("count_context", "context_follow_up"),
            )

        if is_detail_request:
            return self._decision(
                route="detail",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="soil", action="detail", grain="entity", mode="standalone"),
                reason_codes=("detail_request",),
            )

        if should_safe_hint:
            return self._decision(
                route="safe_hint",
                normalized_text=normalized_text,
                normalized_changed=normalized_changed,
                query_shape=QueryShape(subject="soil", action="guidance", grain="none", mode="safe_hint"),
                reason_codes=("safe_hint",),
            )

        return self._decision(
            route="summary",
            normalized_text=normalized_text,
            normalized_changed=normalized_changed,
            query_shape=QueryShape(subject="soil", action="summary", grain="none", mode="standalone"),
            reason_codes=("summary_default",),
        )

    @staticmethod
    def _decision(
        *,
        route: str,
        normalized_text: str,
        normalized_changed: bool,
        query_shape: QueryShape,
        reason_codes: tuple[str, ...],
        list_target: str | None = None,
        group_by: str | None = None,
        route_source: str = "direct",
    ) -> TurnRouteDecision:
        final_source = route_source
        if final_source == "direct" and normalized_changed:
            final_source = "normalized"
        return TurnRouteDecision(
            route=route,
            list_target=list_target,
            group_by=group_by,
            normalized_text=normalized_text,
            route_source=final_source,
            query_shape=query_shape,
            reason_codes=reason_codes,
        )

    def _normalize_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", str(text or "").strip())
        normalized = re.sub(r"([？?]){2,}", "？", normalized)
        normalized = re.sub(r"([。！!]){2,}", r"\1", normalized)
        for source, target in TEXT_NORMALIZATION_RULES:
            normalized = normalized.replace(source, target)
        return normalized

    @staticmethod
    def _classify_subject(text: str) -> str:
        if any(token in text for token in TEMPLATE_TOKENS):
            return "template"
        if "规则" in text:
            return "rule"
        if TurnRouteDecisionService._is_unsupported_derived_analysis_request(text):
            return "unsupported_derived"
        return "soil"

    @staticmethod
    def _current_list_grain(context: dict[str, Any]) -> str:
        return str((context.get("primary_query_spec") or {}).get("grain") or "")

    def _resolve_list_target(self, text: str, context: dict[str, Any]) -> str | None:
        if self._is_group_request(text):
            return None
        if any(
            (
                QueryProfileResolverService.is_latest_record_request(text),
                QueryProfileResolverService.is_count_request(text),
                QueryProfileResolverService.is_field_request(text),
                QueryProfileResolverService.is_compare_request(text),
            )
        ):
            return None

        prior_grain = self._current_list_grain(context)
        has_data_context = context.get("topic_family") == "data"
        has_follow_up_reference = any(token in text for token in ("这些", "这44条", "这44个", "这里的", "刚才", "上面的"))
        has_list_verb = any(token in text for token in ("列出", "列一下", "展示", "查看", "看看", "名单", "列表"))
        has_enumeration_cue = any(token in text for token in LIST_ENUMERATION_TOKENS)
        mentions_alert_records = (
            "预警记录" in text
            or "预警详情" in text
            or "预警明细" in text
            or (any(token in text for token in ("预警", "异常")) and "条" in text)
        )
        mentions_record = (
            mentions_alert_records
            or "记录" in text
            or ("数据" in text and "规则" not in text and not any(token in text for token in TEMPLATE_TOKENS))
        )
        mentions_device = any(token in text for token in ("点位", "设备"))
        mentions_focus_devices = any(token in text for token in ("重点关注的点位", "重点关注点位", "设备名单"))

        if mentions_record and (
            any(token in text for token in ("预警", "异常", "条", "详情", "明细", "列出", "展示"))
            or (has_enumeration_cue and not mentions_device)
        ):
            return LIST_TARGET_ALERT_RECORDS
        if mentions_focus_devices:
            return LIST_TARGET_FOCUS_DEVICES
        if has_data_context and prior_grain == "record_list" and has_follow_up_reference:
            return LIST_TARGET_ALERT_RECORDS
        if mentions_device and any(token in text for token in DETAIL_HINT_TOKENS):
            return LIST_TARGET_FOCUS_DEVICES
        if mentions_device and (
            has_list_verb
            or has_follow_up_reference
            or "只看" in text
            or "筛" in text
            or has_enumeration_cue
        ):
            return LIST_TARGET_FOCUS_DEVICES
        if has_data_context and has_list_verb:
            return LIST_TARGET_ALERT_RECORDS if prior_grain == "record_list" else LIST_TARGET_FOCUS_DEVICES
        return None

    @staticmethod
    def _is_group_request(text: str) -> bool:
        if "归类" in text or "汇总" in text:
            return True
        if TurnRouteDecisionService._is_plain_group_follow_up_phrase(text):
            return True
        lowered = str(text or "").lower()
        if any(marker in lowered for marker in RANKING_MARKERS) and any(token in text for token in ("县", "区", "市", "地区", "地方")):
            if any(token in text for token in ("预警", "异常", "关注")):
                return True
        if "哪个县" in text or "哪个区" in text or "哪个市" in text:
            if any(token in text for token in ("预警", "异常", "关注")):
                return True
        return any(pattern.search(text) for pattern in REGION_GROUP_REQUEST_PATTERNS)

    @staticmethod
    def _is_unsupported_derived_analysis_request(text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False
        lowered = normalized.lower()
        if any(token in normalized for token in ("风险",)) and any(marker in lowered for marker in RANKING_MARKERS):
            return True
        if "最严重" in normalized and "风险" in normalized:
            return True
        if "最严重" in normalized and any(token in normalized for token in ("地方", "地区", "区域", "点位", "设备", "哪里", "哪个")):
            return True
        return False

    @staticmethod
    def _is_plain_group_follow_up_phrase(text: str) -> bool:
        return bool(PLAIN_GROUP_FOLLOW_UP_PATTERN.fullmatch(str(text or "").strip()))

    @staticmethod
    def _is_compare_request(text: str) -> bool:
        return QueryProfileResolverService.is_compare_request(text)

    @staticmethod
    def _has_explicit_detail(text: str, entities: dict[str, Any]) -> bool:
        if SN_PATTERN.search(text) and not any(
            (
                QueryProfileResolverService.is_latest_record_request(text),
                QueryProfileResolverService.is_count_request(text),
                QueryProfileResolverService.is_field_request(text),
                QueryProfileResolverService.is_compare_request(text),
                "怎么样" in text or "情况" in text or "如何" in text,
            )
        ):
            return True
        if not any(entities.get(key) for key in ("province", "city", "county", "sn")):
            return False
        return any(token in text for token in DETAIL_HINT_TOKENS) and not any(
            (
                QueryProfileResolverService.is_count_request(text),
                QueryProfileResolverService.is_field_request(text),
                QueryProfileResolverService.is_compare_request(text),
                "点位详情" in text,
                "记录详情" in text,
            )
        )

    @staticmethod
    def _is_detail_request(text: str, entities: dict[str, Any]) -> bool:
        if SN_PATTERN.search(text) and not any(
            (
                QueryProfileResolverService.is_latest_record_request(text),
                QueryProfileResolverService.is_count_request(text),
                QueryProfileResolverService.is_field_request(text),
                QueryProfileResolverService.is_compare_request(text),
                "怎么样" in text or "情况" in text or "如何" in text,
            )
        ):
            return True
        if any(token in text for token in DETAIL_HINT_TOKENS):
            return True
        return False

    @staticmethod
    def _count_grain(text: str) -> str:
        if any(token in text for token in ("点位", "设备")):
            return "device"
        if any(token in text for token in ("记录", "条")):
            return "record"
        if any(token in text for token in ("地区", "区县", "地方")):
            return "region"
        return "none"

    def _should_follow_up_detail(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        entities: dict[str, Any],
        time_evidence: Any,
        has_explicit_detail: bool,
        is_group_request: bool,
        list_target: str | None,
        is_compare_request: bool,
    ) -> bool:
        if has_explicit_detail:
            return False
        if current_context.get("topic_family") != "data":
            return False
        query_state = current_context.get("query_state") or {}
        if str(query_state.get("capability") or "") != "detail":
            return False
        if is_group_request or list_target or is_compare_request:
            return False
        if any(marker in text for marker in GLOBAL_SCOPE_RESET_MARKERS):
            return False
        if any(pattern.fullmatch(text) for pattern in TIME_ONLY_FOLLOW_UP_PATTERNS):
            return True

        has_explicit_scope = any(entities.get(key) for key in ("province", "city", "county", "sn"))
        time_has_signal = bool(getattr(time_evidence, "has_time_signal", False))
        contextual_prefixes = ("那", "那就", "那边", "这边", "换成", "改成", "还是")
        full_query_reset_tokens = ("怎么样", "情况", "如何", "有没有", "墒情", "数据")

        if any(marker in text for marker in CONTEXTUAL_FOLLOW_UP_MARKERS):
            return bool(has_explicit_scope or time_has_signal)

        if time_has_signal and text.startswith(contextual_prefixes) and not has_explicit_scope:
            return True

        if has_explicit_scope and time_has_signal and any(token in text for token in full_query_reset_tokens):
            return False

        if has_explicit_scope and text.endswith("呢"):
            if text.startswith(contextual_prefixes):
                return True
            if len(text) <= 8 and not any(token in text for token in QUERY_CUE_TOKENS):
                return True

        if time_has_signal and text.startswith(("那", "那就", "换成", "改成")):
            return True

        return False

    def _should_follow_up_count(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        entities: dict[str, Any],
        time_evidence: Any,
        is_group_request: bool,
        list_target: str | None,
        is_compare_request: bool,
    ) -> bool:
        if current_context.get("topic_family") != "data":
            return False
        query_state = current_context.get("query_state") or {}
        if str(query_state.get("capability") or "") != "count":
            return False
        if is_group_request or list_target or is_compare_request:
            return False
        if any(marker in text for marker in GLOBAL_SCOPE_RESET_MARKERS):
            return False
        if any(pattern.fullmatch(text) for pattern in TIME_ONLY_FOLLOW_UP_PATTERNS):
            return True
        has_explicit_scope = any(entities.get(key) for key in ("province", "city", "county", "sn"))
        time_has_signal = bool(getattr(time_evidence, "has_time_signal", False))
        if has_explicit_scope:
            return False
        return bool(time_has_signal and text.startswith(("那", "那就", "换成", "改成", "还是")))

    def _should_return_safe_hint_before_summary(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        entities: dict[str, Any],
        time_evidence: Any,
    ) -> bool:
        if current_context.get("topic_family") == "data":
            return False
        compact = text.replace(" ", "")
        if len(compact) > 6:
            return False
        if any(token in text for token in DOMAIN_INTENT_TOKENS):
            return False
        if getattr(time_evidence, "has_time_signal", False) or getattr(time_evidence, "clarify_reason", ""):
            return False
        return not any(entities.get(key) for key in ("province", "city", "county", "sn"))

    def _should_treat_group_request_as_standalone(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        entities: dict[str, Any],
        time_evidence: Any,
    ) -> bool:
        if current_context.get("topic_family") != "data":
            return self._can_run_standalone_group_query(text=text, entities=entities, time_evidence=time_evidence)
        if getattr(time_evidence, "has_time_signal", False):
            return True
        if any(entities.get(key) for key in ("province", "city", "county", "sn")):
            return True
        return any(token in text for token in ("整体", "全省", "整个", "全部"))

    def _can_run_standalone_group_query(self, *, text: str, entities: dict[str, Any], time_evidence: Any) -> bool:
        if any(token in text for token in ("汇总", "归类", "分组")):
            return True
        if any(token in text for token in ("墒情", "数据", "记录", "含水量", "土壤")):
            return True
        if getattr(time_evidence, "has_time_signal", False):
            return True
        return any(entities.get(key) for key in ("province", "city", "county", "sn"))

    @staticmethod
    def _should_treat_list_request_as_standalone(
        *,
        text: str,
        current_context: dict[str, Any],
        entities: dict[str, Any],
        time_evidence: Any,
    ) -> bool:
        del current_context
        if getattr(time_evidence, "has_time_signal", False):
            return True
        if any(entities.get(key) for key in ("province", "city", "county", "sn")):
            return True
        return any(token in text for token in ("整体", "全省", "整个", "全部"))

    @staticmethod
    def _resolve_group_by(message: str) -> str:
        if "地区" in message or "区域" in message or "地方" in message:
            return "region"
        if "县" in message or "区" in message:
            return "county"
        if "市" in message:
            return "city"
        return "region"

    @staticmethod
    def _grain_for_list_target(list_target: str) -> str:
        if list_target == LIST_TARGET_ALERT_RECORDS:
            return "record"
        if list_target == LIST_TARGET_FOCUS_DEVICES:
            return "device"
        return "none"

    @staticmethod
    def _query_action_from_target(target: dict[str, Any], *, subject_kind: str) -> str:
        capability = str(target.get("capability") or "")
        if capability == "group":
            return "group"
        if capability == "list":
            return "list"
        if capability == "detail":
            return "detail"
        if capability == "compare":
            return "compare"
        if subject_kind == "region":
            return "group"
        if subject_kind in {"device", "record"}:
            return "list"
        return "summary"

    @staticmethod
    def _query_grain_from_target(target: dict[str, Any], *, subject_kind: str) -> str:
        grain = str(target.get("grain") or "")
        if grain == "record_list":
            return "record"
        if grain == "device_list":
            return "device"
        if grain == "region_group":
            return "region"
        if grain in {"city_group", "city"}:
            return "city"
        if grain in {"county_group", "county"}:
            return "county"
        if grain == "entity_detail":
            return "entity"
        if subject_kind == "region":
            return "region"
        if subject_kind == "device":
            return "device"
        if subject_kind == "record":
            return "record"
        return "none"

    @staticmethod
    def _list_target_from_action_target(target: dict[str, Any]) -> str | None:
        capability = str(target.get("capability") or "")
        if capability != "list":
            return None
        source_snapshot_kind = str(target.get("source_snapshot_kind") or "")
        if source_snapshot_kind == LIST_TARGET_ALERT_RECORDS:
            return LIST_TARGET_ALERT_RECORDS
        return LIST_TARGET_FOCUS_DEVICES


__all__ = ["QueryShape", "TurnRouteDecision", "TurnRouteDecisionService"]

"""Deterministic follow-up intent resolver for chat-v2 context inheritance."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


FOLLOW_UP_MAX_TURN_GAP = 5
_PRONOUN_MARKERS = ("那个", "这个", "上面那个", "上面的", "这里的", "其中")
_SUBSET_MARKERS = ("只看", "筛", "过滤")
_SWITCH_CAPABILITY_MARKERS = ("详情", "明细", "规则", "模板")
_ORDINAL_PATTERN = re.compile(r"第([0-9一二两三四五六七八九十]+)个")

_CHINESE_ORDINALS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


@dataclass(frozen=True)
class FollowUpIntentResult:
    operation: str = "standalone"
    confidence: float = 1.0
    chosen_target: dict[str, Any] | None = None
    selected_ref: dict[str, Any] | None = None
    new_slots: dict[str, Any] = field(default_factory=dict)
    inherit_slots: list[str] = field(default_factory=list)
    clarify_reason: str = ""
    clarify_message: str = ""
    rejected_candidates: list[str] = field(default_factory=list)
    uncertain: bool = False


class FollowUpIntentResolverService:
    """Classify whether a message should inherit, replace, or clarify context."""

    def resolve(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        extracted_entities: dict[str, list[str]],
        time_has_signal: bool,
        turn_id: int,
    ) -> FollowUpIntentResult:
        normalized = str(text or "").strip()
        latest_target = self._latest_target(current_context)
        has_explicit_entity = any(extracted_entities.get(key) for key in ("province", "city", "county", "sn"))
        new_slots = self._new_slots_from_entities(extracted_entities)

        if current_context.get("closed"):
            if has_explicit_entity and time_has_signal:
                return FollowUpIntentResult(operation="standalone")
            if has_explicit_entity:
                return FollowUpIntentResult(
                    operation="clarify",
                    clarify_reason="closed_context",
                    clarify_message="上一轮话题已经结束，请重新补充时间段或时间范围，例如最近7天或最近1个月。",
                )
            return FollowUpIntentResult(
                operation="clarify",
                clarify_reason="closed_context",
                clarify_message="上一轮话题已经结束，请重新说明地区、设备和时间范围。",
            )

        if latest_target and turn_id - int(latest_target.get("last_active_turn_id") or 0) > FOLLOW_UP_MAX_TURN_GAP:
            if self._looks_like_follow_up(normalized, time_has_signal, has_explicit_entity):
                return FollowUpIntentResult(
                    operation="clarify",
                    chosen_target=latest_target,
                    clarify_reason="stale_target",
                    clarify_message="上一次查询上下文已经过期了，请重新说明地区、设备或时间范围。",
                )
            return FollowUpIntentResult(operation="standalone")

        if self._is_negative_correction(normalized) and latest_target and has_explicit_entity:
            return FollowUpIntentResult(
                operation="correct_slot",
                confidence=0.99,
                chosen_target=latest_target,
                new_slots=new_slots,
                inherit_slots=["time"],
            )

        if any(marker in normalized for marker in _SUBSET_MARKERS):
            return FollowUpIntentResult(
                operation="subset",
                confidence=0.95,
                chosen_target=latest_target,
                new_slots=new_slots,
                inherit_slots=["time"],
            )

        if self._contains_global_scope_reset(normalized):
            return FollowUpIntentResult(operation="standalone", confidence=0.95)

        if not has_explicit_entity:
            selected_ref, ref_failure = self._resolve_result_ref(normalized, current_context)
            if selected_ref is not None:
                return FollowUpIntentResult(
                    operation="drilldown_ref",
                    confidence=0.95,
                    chosen_target=latest_target,
                    selected_ref=selected_ref,
                    inherit_slots=["time"],
                )
            if ref_failure is not None:
                return ref_failure

        if latest_target and any(marker in normalized for marker in _SWITCH_CAPABILITY_MARKERS):
            return FollowUpIntentResult(
                operation="switch_capability",
                confidence=0.9,
                chosen_target=latest_target,
                new_slots=new_slots,
                inherit_slots=["time"],
            )

        if latest_target and has_explicit_entity and not time_has_signal:
            return FollowUpIntentResult(
                operation="replace_slot",
                confidence=0.95,
                chosen_target=latest_target,
                new_slots=new_slots,
                inherit_slots=["time"],
            )

        if latest_target and time_has_signal and not has_explicit_entity:
            return FollowUpIntentResult(
                operation="inherit",
                confidence=0.9,
                chosen_target=latest_target,
                inherit_slots=["scope"],
            )

        if latest_target and self._looks_like_contextual_follow_up(normalized):
            return FollowUpIntentResult(
                operation="inherit",
                confidence=0.75,
                chosen_target=latest_target,
                inherit_slots=["scope", "time"],
                uncertain=True,
            )

        return FollowUpIntentResult(operation="standalone")

    @staticmethod
    def _latest_target(current_context: dict[str, Any]) -> dict[str, Any] | None:
        targets = current_context.get("follow_up_targets") or []
        return targets[0] if targets else None

    @staticmethod
    def _new_slots_from_entities(extracted_entities: dict[str, list[str]]) -> dict[str, Any]:
        slots = {}
        for key in ("province", "city", "county", "sn"):
            values = extracted_entities.get(key) or []
            if values:
                slots[key] = values[-1]
        return slots

    @staticmethod
    def _is_negative_correction(text: str) -> bool:
        return text.startswith("不是") or text.startswith("不对") or text.startswith("不，是") or text.startswith("不对，是")

    @staticmethod
    def _looks_like_contextual_follow_up(text: str) -> bool:
        if not text:
            return False
        if text.endswith("呢"):
            return True
        return any(marker in text for marker in _PRONOUN_MARKERS)

    def _looks_like_follow_up(self, text: str, time_has_signal: bool, has_explicit_entity: bool) -> bool:
        return self._looks_like_contextual_follow_up(text) or time_has_signal or has_explicit_entity

    @staticmethod
    def _contains_global_scope_reset(text: str) -> bool:
        return any(token in text for token in ("整体", "全省", "整个", "全部", "哪里", "哪个地方", "最严重", "排名", "排行"))

    def _resolve_result_ref(
        self,
        text: str,
        current_context: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, FollowUpIntentResult | None]:
        refs = current_context.get("result_refs") or []
        if not refs:
            return None, None

        ordinal = self._parse_ordinal(text)
        desired_type = self._desired_ref_type(text)
        candidates = [ref for ref in refs if desired_type is None or ref.get("ref_type") == desired_type]

        if ordinal is not None:
            for ref in candidates:
                if int(ref.get("ordinal") or 0) == ordinal:
                    return ref, None
            return None, FollowUpIntentResult(
                operation="clarify",
                clarify_reason="missing_ref",
                clarify_message="我没法确定你指的是哪一项，请直接说具体地区、设备，或重新列出结果后再指定。",
            )

        if not any(marker in text for marker in _PRONOUN_MARKERS):
            return None, None
        if len(candidates) == 1:
            return candidates[0], None
        if len(candidates) == 0:
            return None, FollowUpIntentResult(
                operation="clarify",
                clarify_reason="missing_ref",
                clarify_message="当前没有可以直接承接的结果项，请直接说具体地区、设备或时间范围。",
            )
        return None, FollowUpIntentResult(
            operation="clarify",
            clarify_reason="ambiguous_ref",
            clarify_message="你这次指代的对象还不够明确，请直接说具体地区、设备，或用“第一个/第二个”来指定。",
            rejected_candidates=[str(ref.get("label") or "") for ref in candidates],
        )

    @staticmethod
    def _desired_ref_type(text: str) -> str | None:
        if "设备" in text or "点位" in text:
            return "device"
        if "地区" in text or "县" in text or "市" in text:
            return "region"
        return None

    def _parse_ordinal(self, text: str) -> int | None:
        match = _ORDINAL_PATTERN.search(text)
        if not match:
            return None
        raw = match.group(1)
        if raw.isdigit():
            return int(raw)
        if raw == "十":
            return 10
        if "十" in raw:
            left, _, right = raw.partition("十")
            tens = _CHINESE_ORDINALS.get(left, 1 if left == "" else None)
            ones = _CHINESE_ORDINALS.get(right, 0 if right == "" else None)
            if tens is None or ones is None:
                return None
            return tens * 10 + ones
        return _CHINESE_ORDINALS.get(raw)


__all__ = ["FollowUpIntentResolverService", "FollowUpIntentResult", "FOLLOW_UP_MAX_TURN_GAP"]

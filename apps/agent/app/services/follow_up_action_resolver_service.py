"""Resolve expandable follow-up result objects for chat-v2."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from app.services.follow_up_intent_resolver_service import FOLLOW_UP_MAX_TURN_GAP


_COUNT_PATTERN = re.compile(r"([0-9一二两三四五六七八九十百]+)\s*(个|条)?")
_ORDINAL_PATTERN = re.compile(r"第([0-9一二两三四五六七八九十百]+)个")
_REF_MARKERS = ("上面那个", "那个", "这个", "其中", "这里的", "上面的")
_BLOCKING_TOKENS = ("最严重", "排名", "排行", "为什么", "原因", "规则", "模板")
_FOLLOW_UP_CUES = ("详情", "明细", "列出", "看看", "哪些", "呢", "这些", "这几个", "那些")

_CHINESE_NUMERALS = {
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
    "百": 100,
}

_SUBJECT_ALIASES = {
    "record": ("预警记录", "异常记录", "记录"),
    "device": ("重点关注点位", "点位", "设备"),
    "region": ("地区", "区域", "地方"),
}


@dataclass(frozen=True)
class FollowUpActionResult:
    operation: str = "none"
    selected_action_target: dict[str, Any] | None = None
    subject_kind: str = ""
    parsed_count: int | None = None
    clarify_reason: str = ""
    clarify_message: str = ""
    rejected_candidates: list[str] = field(default_factory=list)


class FollowUpActionResolverService:
    """Resolve metric-like follow-up objects into structured executable targets."""

    def resolve(
        self,
        *,
        text: str,
        current_context: dict[str, Any],
        turn_id: int,
    ) -> FollowUpActionResult:
        normalized = str(text or "").strip()
        if not normalized or current_context.get("closed") or current_context.get("topic_family") != "data":
            return FollowUpActionResult()
        if any(token in normalized for token in _BLOCKING_TOKENS):
            return FollowUpActionResult()
        if _ORDINAL_PATTERN.search(normalized) or any(marker in normalized for marker in _REF_MARKERS):
            return FollowUpActionResult()

        subject_kind = self._parse_subject_kind(normalized)
        if not subject_kind:
            return FollowUpActionResult()

        parsed_count = self._parse_count(normalized)
        has_follow_up_cue = parsed_count is not None or any(token in normalized for token in _FOLLOW_UP_CUES)
        if not has_follow_up_cue:
            return FollowUpActionResult()

        all_candidates = [
            target
            for target in current_context.get("action_targets") or []
            if target.get("subject_kind") == subject_kind
        ]
        if not all_candidates:
            return FollowUpActionResult(subject_kind=subject_kind, parsed_count=parsed_count)

        live_candidates = [
            target
            for target in all_candidates
            if turn_id - int(target.get("last_active_turn_id") or 0) <= FOLLOW_UP_MAX_TURN_GAP
        ]
        if not live_candidates:
            return FollowUpActionResult(
                operation="clarify",
                subject_kind=subject_kind,
                parsed_count=parsed_count,
                clarify_reason="stale_target",
                clarify_message="上一次结果对象已经过期了，请重新发起一次数据查询后再继续追问。",
                rejected_candidates=[str(target.get("label") or "") for target in all_candidates],
            )

        if parsed_count is not None:
            exact = [target for target in live_candidates if self._target_count(target) == parsed_count]
            if len(exact) == 1:
                return FollowUpActionResult(
                    operation="expand_target",
                    selected_action_target=exact[0],
                    subject_kind=subject_kind,
                    parsed_count=parsed_count,
                )
            if len(exact) > 1:
                return FollowUpActionResult(
                    operation="clarify",
                    subject_kind=subject_kind,
                    parsed_count=parsed_count,
                    clarify_reason="ambiguous_target",
                    clarify_message="我还不能确定你要展开哪一类结果，请直接说要看地区、点位还是记录。",
                    rejected_candidates=[str(target.get("label") or "") for target in exact],
                )
            return FollowUpActionResult(
                operation="clarify",
                subject_kind=subject_kind,
                parsed_count=parsed_count,
                clarify_reason="count_mismatch",
                clarify_message=self._count_mismatch_message(subject_kind=subject_kind, candidates=live_candidates),
                rejected_candidates=[str(target.get("label") or "") for target in live_candidates],
            )

        if len(live_candidates) == 1:
            return FollowUpActionResult(
                operation="expand_target",
                selected_action_target=live_candidates[0],
                subject_kind=subject_kind,
                parsed_count=None,
            )

        return FollowUpActionResult(
            operation="clarify",
            subject_kind=subject_kind,
            parsed_count=None,
            clarify_reason="ambiguous_target",
            clarify_message="你这次要展开的结果对象还不够明确，请直接说地区、点位或记录。",
            rejected_candidates=[str(target.get("label") or "") for target in live_candidates],
        )

    @staticmethod
    def _parse_subject_kind(text: str) -> str:
        best_match = ("", "")
        for subject_kind, aliases in _SUBJECT_ALIASES.items():
            for alias in aliases:
                if alias in text and len(alias) > len(best_match[1]):
                    best_match = (subject_kind, alias)
        return best_match[0]

    def _parse_count(self, text: str) -> int | None:
        match = _COUNT_PATTERN.search(text)
        if not match:
            return None
        raw = str(match.group(1) or "").strip()
        if not raw:
            return None
        if raw.isdigit():
            return int(raw)
        return self._chinese_number(raw)

    @staticmethod
    def _target_count(target: dict[str, Any]) -> int | None:
        count = target.get("count")
        if count is None:
            return None
        try:
            return int(count)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _count_mismatch_message(*, subject_kind: str, candidates: list[dict[str, Any]]) -> str:
        label = {
            "region": "地区",
            "device": "点位",
            "record": "记录",
        }.get(subject_kind, "结果")
        counts = [count for count in (FollowUpActionResolverService._target_count(item) for item in candidates) if count is not None]
        if len(counts) == 1:
            return f"当前这轮可继续展开的是 {counts[0]} 个{label}，请按这个结果继续追问，或先重新查询。"
        if counts:
            joined = "、".join(str(count) for count in counts)
            return f"当前可继续展开的{label}数量有 {joined}，请说得更具体一些。"
        return f"当前这轮还没有可直接展开的{label}结果，请先重新查询。"

    @staticmethod
    def _chinese_number(raw: str) -> int | None:
        if raw == "十":
            return 10
        if "百" in raw:
            left, _, right = raw.partition("百")
            hundreds = _CHINESE_NUMERALS.get(left, 1 if left == "" else None)
            rest = FollowUpActionResolverService._chinese_number(right) if right else 0
            if hundreds is None or rest is None:
                return None
            return hundreds * 100 + rest
        if "十" in raw:
            left, _, right = raw.partition("十")
            tens = _CHINESE_NUMERALS.get(left, 1 if left == "" else None)
            ones = _CHINESE_NUMERALS.get(right, 0 if right == "" else None)
            if tens is None or ones is None:
                return None
            return tens * 10 + ones
        return _CHINESE_NUMERALS.get(raw)


__all__ = ["FollowUpActionResolverService", "FollowUpActionResult"]

"""Centralized top-level route decision for deterministic data-answer turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TurnRouteDecision:
    route: str
    list_target: str | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


class TurnRouteDecisionService:
    """Choose the single top-level route for one chat turn.

    This keeps precedence in one place so standalone queries, follow-up
    expansions, list/group/detail handlers, and summary fallback do not
    compete in multiple layers.
    """

    def decide(
        self,
        *,
        has_explicit_detail: bool,
        should_follow_up_detail: bool,
        is_group_request: bool,
        should_group_standalone: bool,
        list_target: str | None,
        should_list_standalone: bool,
        action_result: Any | None,
        is_compare_request: bool,
        is_detail_request: bool,
        should_safe_hint_before_summary: bool,
    ) -> TurnRouteDecision:
        if has_explicit_detail:
            return TurnRouteDecision(route="explicit_detail", reason_codes=("explicit_detail",))

        if is_group_request and should_group_standalone:
            return TurnRouteDecision(
                route="standalone_group",
                reason_codes=("group_request", "standalone_signals"),
            )

        if list_target and should_list_standalone:
            return TurnRouteDecision(
                route="standalone_list",
                list_target=list_target,
                reason_codes=("list_request", "standalone_signals"),
            )

        action_operation = str(getattr(action_result, "operation", "") or "")
        if action_operation == "clarify":
            return TurnRouteDecision(
                route="follow_up_action_clarify",
                reason_codes=("action_target_clarify",),
            )
        if action_operation == "expand_target":
            return TurnRouteDecision(
                route="follow_up_action_expand",
                reason_codes=("action_target_expand",),
            )

        if list_target:
            return TurnRouteDecision(
                route="follow_up_list",
                list_target=list_target,
                reason_codes=("list_request", "context_follow_up"),
            )

        if is_group_request:
            return TurnRouteDecision(
                route="follow_up_group",
                reason_codes=("group_request", "context_follow_up"),
            )

        if is_compare_request:
            return TurnRouteDecision(route="compare", reason_codes=("compare_request",))

        if should_follow_up_detail:
            return TurnRouteDecision(route="follow_up_detail", reason_codes=("detail_context", "context_follow_up"))

        if is_detail_request:
            return TurnRouteDecision(route="detail", reason_codes=("detail_request",))

        if should_safe_hint_before_summary:
            return TurnRouteDecision(route="safe_hint", reason_codes=("safe_hint",))

        return TurnRouteDecision(route="summary", reason_codes=("summary_default",))


__all__ = ["TurnRouteDecision", "TurnRouteDecisionService"]

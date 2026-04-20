from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FlowState:
    request_id: str
    session_id: str
    turn_id: int
    user_input: str
    trace_id: str = ""
    channel: str = "web"
    timezone: str = "Asia/Shanghai"
    input_type: str | None = None
    intent: str | None = None
    answer_type: str | None = None
    route_target: str | None = None
    raw_slots: dict[str, Any] = field(default_factory=dict)
    merged_slots: dict[str, Any] = field(default_factory=dict)
    context_used: dict[str, Any] = field(default_factory=dict)
    business_time: dict[str, Any] = field(default_factory=dict)
    execution_gate_result: dict[str, Any] = field(default_factory=dict)
    query_plan: dict[str, Any] = field(default_factory=dict)
    query_result: dict[str, Any] = field(default_factory=dict)
    rule_result: dict[str, Any] = field(default_factory=dict)
    template_result: dict[str, Any] = field(default_factory=dict)
    advice_result: dict[str, Any] = field(default_factory=dict)
    answer_bundle: dict[str, Any] = field(default_factory=dict)
    node_trace: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    final_status: str | None = None
    step_count: int = 0
    retry_count: int = 0
    node_visit_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class NodeResult:
    next_action: str
    state_patch: dict[str, Any] = field(default_factory=dict)
    node_status: str = "success"
    debug_payload: dict[str, Any] = field(default_factory=dict)

"""Pydantic state models that define the Agent Flow contract.

These bundles are the typed schema for everything the nodes pass to each other:
slots, business time, execution gate decisions, query plans/results, rule
results, rendered templates, advice text, final answer, traces, and errors.
The shape mirrors the plans so tests can compare implementation and design.
"""

from __future__ import annotations


from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import AnswerType, InputType, IntentType

class BundleModel(BaseModel):
    """Base bundle with dict-like helpers used by Flow patch merging."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style getter for code that treats bundles like mappings."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Allow `bundle["field"]` access in legacy helper code."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow controlled item assignment while preserving Pydantic validation."""
        setattr(self, key, value)

    def update(self, values: dict[str, Any] | BaseModel) -> None:
        """Merge known fields from a dict or another Pydantic model."""
        payload = values.model_dump(exclude_none=False) if isinstance(values, BaseModel) else values
        for key, value in payload.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def items(self):
        """Return non-empty bundle items, matching dict-like behavior."""
        return self.model_dump(exclude_none=True).items()

    def __iter__(self):
        """Iterate over non-empty bundle items."""
        return iter(self.model_dump(exclude_none=True).items())

    def __contains__(self, key: str) -> bool:
        """Return true when the bundle field exists and is not `None`."""
        return getattr(self, key, None) is not None


class SlotBundle(BundleModel):
    """Parsed and merged user slots used for query planning."""

    city_name: str | None = None
    county_name: str | None = None
    town_name: str | None = None
    device_sn: str | None = None
    target_date: str | None = None
    time_range: str | None = None
    batch_id: str | None = None
    follow_up: bool = False
    top_n: int | None = None
    batch_devices: str | None = None
    trend: str | None = None
    aggregation: str | None = None
    metric: str | None = None
    audience: str | None = None
    render_mode: str | None = None
    need_template: bool = False
    region_exists: bool | None = None
    device_exists: bool | None = None
    latest_batch: bool | None = None


class BusinessTimeBundle(BundleModel):
    """Resolved business-time window based on imported data timestamps."""

    latest_business_time: str | None = None
    latest_batch_id: str | None = None
    resolved_batch_id: str | None = None
    resolved_time_range: str | None = None
    resolution_mode: str | None = None
    time_basis: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class ExecutionGateBundle(BundleModel):
    """Decision payload produced before data query execution."""

    tool_name: str | None = None
    decision: str | None = None
    allow_execute: bool = True
    requested_days: int | None = None
    resolved_days: int | None = None
    reason: str | None = None
    policy_decision: str | None = None
    violations: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None
    must_clarify: bool = False
    blocked: bool = False
    shrink_applied: bool = False
    effective_business_time: BusinessTimeBundle | None = None
    effective_slots: SlotBundle | None = None
    clarify_message: str | None = None
    block_message: str | None = None


class QueryPlanBundle(BundleModel):
    """Fixed SQL-template plan plus filters, time range, and audit metadata."""

    query_type: str | None = None
    sql_template: str | None = None
    fallback_scenario: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    group_by: list[str] | None = None
    metrics: list[str] | None = None
    order_by: list[str] | None = None
    limit_size: int | None = None
    time_range: dict[str, Any] = Field(default_factory=dict)
    slots: dict[str, Any] = Field(default_factory=dict)
    business_time: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)


class QueryResultBundle(BundleModel):
    """Normalized query result returned by `SoilQueryService`."""

    records: list[dict[str, Any]] = Field(default_factory=list)
    aggregation: str | None = None
    top_n: int | None = None
    period_record_count: int | None = None
    device_record_count: int | None = None
    region_record_count: int | None = None
    latest_sample_time: str | None = None


class RuleResultBundle(BundleModel):
    """Rule-engine result and route hint for template/advice generation."""

    route_action: str | None = None
    evaluated_records: list[dict[str, Any]] = Field(default_factory=list)


class TemplateResultBundle(BundleModel):
    """Rendered warning-template text and follow-up route hint."""

    route_action: str | None = None
    rendered_text: str = ""
    render_mode: str | None = None


class AdviceResultBundle(BundleModel):
    """Conservative management-advice text."""

    advice_text: str = ""


class AnswerBundle(BundleModel):
    """Final answer text shown to the user."""

    final_answer: str = ""


class FlowState(BaseModel):
    """Mutable request state that travels through every Flow node."""

    model_config = ConfigDict(validate_assignment=True)

    request_id: str
    trace_id: str = ""
    session_id: str
    turn_id: int
    user_input: str
    channel: str = "web"
    timezone: str = "Asia/Shanghai"

    input_type: InputType | None = None
    intent: IntentType | None = None
    answer_type: AnswerType | None = None
    route_target: str | None = None

    raw_slots: SlotBundle = Field(default_factory=SlotBundle)
    merged_slots: SlotBundle = Field(default_factory=SlotBundle)
    context_used: dict[str, Any] = Field(default_factory=dict)

    business_time: BusinessTimeBundle = Field(default_factory=BusinessTimeBundle)
    execution_gate_result: ExecutionGateBundle = Field(default_factory=ExecutionGateBundle)

    query_plan: QueryPlanBundle = Field(default_factory=QueryPlanBundle)
    query_result: QueryResultBundle = Field(default_factory=QueryResultBundle)
    rule_result: RuleResultBundle = Field(default_factory=RuleResultBundle)
    template_result: TemplateResultBundle = Field(default_factory=TemplateResultBundle)
    advice_result: AdviceResultBundle = Field(default_factory=AdviceResultBundle)
    answer_bundle: AnswerBundle = Field(default_factory=AnswerBundle)

    query_log_entries: list[dict[str, Any]] = Field(default_factory=list)
    context_to_save: dict[str, Any] | None = None

    node_trace: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    final_status: str | None = None
    step_count: int = 0
    retry_count: int = 0
    node_visit_counts: dict[str, int] = Field(default_factory=dict)


class NodeResult(BaseModel):
    """Standard return value for one Flow node execution."""

    next_action: str
    state_patch: dict[str, Any] = Field(default_factory=dict)
    node_status: str = "success"
    debug_payload: dict[str, Any] = Field(default_factory=dict)

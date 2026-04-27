"""Pydantic state models that define the Agent Flow contract.

These bundles are the typed schema for everything the nodes pass to each other:
query results, final answer, traces, and errors.
The shape mirrors the LLM + Function Calling 5-node architecture.
"""

from __future__ import annotations


from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import AnswerType, FallbackReason, GuidanceReason, InputType, IntentType, OutputMode

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


class QueryResultBundle(BundleModel):
    """Normalized query result returned by tool executors."""

    records: list[dict[str, Any]] = Field(default_factory=list)
    aggregation: str | None = None
    top_n: int | None = None
    period_record_count: int | None = None
    device_record_count: int | None = None
    region_record_count: int | None = None
    latest_create_time: str | None = None


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
    output_mode: OutputMode | None = None
    guidance_reason: GuidanceReason | None = None
    fallback_reason: FallbackReason | None = None
    route_target: str | None = None

    conversation_closed: bool = False

    query_result: QueryResultBundle = Field(default_factory=QueryResultBundle)
    answer_bundle: AnswerBundle = Field(default_factory=AnswerBundle)

    query_log_entries: list[dict[str, Any]] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    answer_facts: dict[str, Any] = Field(default_factory=dict)

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

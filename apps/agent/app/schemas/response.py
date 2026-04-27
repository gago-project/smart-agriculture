"""Schema definitions for response within the soil agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.enums import AnswerType, FallbackReason, GuidanceReason, InputType, IntentType, OutputMode


class ChatResponse(BaseModel):
    """Response payload returned by the soil agent chat endpoints."""
    session_id: str
    turn_id: int
    request_id: str
    trace_id: str
    input_type: InputType | None = None
    intent: IntentType | None = None
    answer_type: AnswerType | None = None
    output_mode: OutputMode | None = None
    guidance_reason: GuidanceReason | None = None
    fallback_reason: FallbackReason | None = None
    final_answer: str = ""
    should_query: bool = False
    conversation_closed: bool = False
    status: str = "ok"
    query_result: dict[str, Any] = Field(default_factory=dict)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    answer_facts: dict[str, Any] = Field(default_factory=dict)
    node_trace: list[str] = Field(default_factory=list)
    final_status: str | None = None

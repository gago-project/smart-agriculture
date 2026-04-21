from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.enums import AnswerType, InputType, IntentType


class ChatResponse(BaseModel):
    session_id: str
    turn_id: int
    request_id: str
    trace_id: str
    input_type: InputType | None = None
    intent: IntentType | None = None
    answer_type: AnswerType | None = None
    final_answer: str = ""
    should_query: bool = False
    status: str = "ok"
    merged_slots: dict[str, Any] = Field(default_factory=dict)
    context_used: dict[str, Any] = Field(default_factory=dict)
    business_time: dict[str, Any] = Field(default_factory=dict)
    execution_gate_result: dict[str, Any] = Field(default_factory=dict)
    query_plan: dict[str, Any] = Field(default_factory=dict)
    query_result: dict[str, Any] = Field(default_factory=dict)
    rule_result: dict[str, Any] = Field(default_factory=dict)
    template_result: dict[str, Any] = Field(default_factory=dict)
    advice_result: dict[str, Any] = Field(default_factory=dict)
    node_trace: list[str] = Field(default_factory=list)
    final_status: str | None = None

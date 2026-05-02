"""Request schemas for the deterministic soil-agent HTTP contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatV2Request(BaseModel):
    """Request payload for the deterministic server-session chat contract."""

    model_config = ConfigDict(populate_by_name=True)

    user_input: str = Field(..., min_length=1, alias="message")
    session_id: str
    turn_id: int
    timezone: str = "Asia/Shanghai"
    current_context: dict[str, Any] | None = None

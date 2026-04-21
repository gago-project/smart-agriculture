from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str | None = None
    user_input: str = Field(..., min_length=1, alias="message")
    session_id: str = "default"
    turn_id: int = 1
    channel: str = "web"
    timezone: str = "Asia/Shanghai"

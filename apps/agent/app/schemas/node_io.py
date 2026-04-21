from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeResultContract(BaseModel):
    next_action: str
    state_patch: dict[str, Any] = Field(default_factory=dict)

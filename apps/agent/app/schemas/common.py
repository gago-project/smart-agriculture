from __future__ import annotations

from pydantic import BaseModel


class MessageEnvelope(BaseModel):
    status: str = "ok"

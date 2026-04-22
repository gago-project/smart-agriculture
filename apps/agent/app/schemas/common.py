"""Schema definitions for common within the soil agent."""

from __future__ import annotations

from pydantic import BaseModel


class MessageEnvelope(BaseModel):
    """Small response envelope shared by lightweight API payloads."""
    status: str = "ok"

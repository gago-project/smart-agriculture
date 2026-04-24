"""Schema definitions for soil within the soil agent."""

from __future__ import annotations

from pydantic import BaseModel


class SoilRecord(BaseModel):
    """Schema describing one soil-moisture fact record."""
    sn: str
    city: str | None = None
    county: str | None = None
    create_time: str
    water20cm: float | None = None

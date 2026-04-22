"""Schema definitions for soil within the soil agent."""

from __future__ import annotations

from pydantic import BaseModel


class SoilRecord(BaseModel):
    """Schema describing one soil-moisture fact record."""
    device_sn: str
    city_name: str | None = None
    county_name: str | None = None
    sample_time: str
    water20cm: float | None = None

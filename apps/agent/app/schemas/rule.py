"""Schema definitions for rule within the soil agent."""

from __future__ import annotations

from pydantic import BaseModel


class RuleEvaluation(BaseModel):
    """Schema for one normalized rule-evaluation result."""
    soil_status: str
    warning_level: str
    display_label: str

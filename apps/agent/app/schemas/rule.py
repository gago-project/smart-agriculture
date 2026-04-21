from __future__ import annotations

from pydantic import BaseModel


class RuleEvaluation(BaseModel):
    soil_status: str
    warning_level: str
    display_label: str

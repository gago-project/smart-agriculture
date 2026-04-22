"""Repository helpers for rule repository within the soil agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SoilRuleProfile:
    """Structured warning-threshold values loaded by the rule repository."""
    rule_name: str
    heavy_drought_max: float
    waterlogging_min: float
    device_fault_water20: float
    device_fault_t20: float


class RuleRepository:
    """Repository helper for rule."""
    async def get_active_rule_profile(self) -> SoilRuleProfile:
        """Return the active soil-warning rule profile."""
        return SoilRuleProfile(
            rule_name="soil_warning_v1",
            heavy_drought_max=50.0,
            waterlogging_min=150.0,
            device_fault_water20=0.0,
            device_fault_t20=0.0,
        )

    async def get_warning_rule_metadata(self) -> dict[str, Any]:
        """Return flattened warning-rule metadata for service callers."""
        profile = await self.get_active_rule_profile()
        return {
            "rule_name": profile.rule_name,
            "heavy_drought_max": profile.heavy_drought_max,
            "waterlogging_min": profile.waterlogging_min,
            "device_fault_water20": profile.device_fault_water20,
            "device_fault_t20": profile.device_fault_t20,
        }

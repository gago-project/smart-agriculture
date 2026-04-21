from __future__ import annotations

"""Region and device existence resolver.

This service performs lightweight validation before SQL planning.  It does not
rewrite region names or invent aliases; it only marks whether an explicit
device/region appears in the current fact table so fallback SQL-07 can explain
empty-data cases accurately.
"""

from typing import Any

from app.repositories.soil_repository import SoilRepository


class RegionResolveService:
    """Validate parsed region/device slots against MySQL facts."""

    def __init__(self, repository: SoilRepository):
        """Repository provides async existence checks."""
        self.repository = repository

    async def resolve(self, *, slots: dict[str, Any], intent: str) -> dict[str, Any]:
        """Return slots plus `region_exists` and `device_exists` booleans."""
        del intent
        resolved = dict(slots)
        resolved["region_exists"] = True
        resolved["device_exists"] = True
        if slots.get("device_sn") and not await self.repository.device_exists_async(slots["device_sn"]):
            resolved["device_exists"] = False
        region_name = slots.get("town_name") or slots.get("county_name") or slots.get("city_name")
        if region_name and not await self.repository.region_exists_async(region_name):
            resolved["region_exists"] = False
        return resolved


__all__ = ["RegionResolveService"]

"""Restricted Flow node implementation for time resolve."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.soil_query_service import SoilQueryService
from app.services.time_service import TimeResolveService


class TimeResolveNode(BaseNode):
    """Flow node for the time resolve stage."""
    def __init__(self, service: TimeResolveService, soil_query_service: SoilQueryService):
        """Initialize the time resolve node."""
        super().__init__("time_resolve", ("continue",), ("business_time", "merged_slots"))
        self.service = service
        self.soil_query_service = soil_query_service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        latest_business_time = await self.soil_query_service.fetch_latest_business_time_if_needed(
            slots=state.merged_slots,
            intent=state.intent or "",
        )
        business_time = self.service.resolve(
            slots=state.merged_slots,
            latest_business_time=latest_business_time,
            timezone=state.timezone,
            inherited_window={
                "start_time": state.merged_slots.get("inherited_start_time"),
                "end_time": state.merged_slots.get("inherited_end_time"),
                "time_label": state.merged_slots.get("time_range"),
                "time_explicit": state.merged_slots.get("inherited_time_explicit"),
            },
            inherit_resolved_window=bool(state.merged_slots.get("inherited_start_time") and state.merged_slots.get("inherited_end_time")),
        )
        return self.ensure_result(
            NodeResult(
                next_action="continue",
                state_patch={
                    "business_time": business_time,
                    "merged_slots": {
                        "resolved_start_time": business_time.get("start_time"),
                        "resolved_end_time": business_time.get("end_time"),
                    },
                },
            )
        )

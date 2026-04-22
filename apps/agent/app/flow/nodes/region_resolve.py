"""Restricted Flow node implementation for region resolve."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.region_service import RegionResolveService


class RegionResolveNode(BaseNode):
    """Flow node for the region resolve stage."""
    def __init__(self, service: RegionResolveService):
        """Initialize the region resolve node."""
        super().__init__("region_resolve", ("continue",), ("merged_slots",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        resolved_slots = await self.service.resolve(slots=state.merged_slots, intent=state.intent or "")
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"merged_slots": resolved_slots}))

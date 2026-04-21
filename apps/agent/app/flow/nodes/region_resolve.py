from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.region_service import RegionResolveService


class RegionResolveNode(BaseNode):
    def __init__(self, service: RegionResolveService):
        super().__init__("region_resolve", ("continue",), ("merged_slots",))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        resolved_slots = await self.service.resolve(slots=state.merged_slots, intent=state.intent or "")
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"merged_slots": resolved_slots}))

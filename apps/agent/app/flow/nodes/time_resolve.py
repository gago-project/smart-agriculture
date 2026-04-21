from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.soil_query_service import SoilQueryService
from app.services.time_service import TimeResolveService


class TimeResolveNode(BaseNode):
    def __init__(self, service: TimeResolveService, soil_query_service: SoilQueryService):
        super().__init__("time_resolve", ("continue",), ("business_time",))
        self.service = service
        self.soil_query_service = soil_query_service

    async def run(self, state: FlowState) -> NodeResult:
        latest_business_time = await self.soil_query_service.fetch_latest_business_time_if_needed(
            slots=state.merged_slots,
            intent=state.intent or "",
        )
        latest_batch_id = await self.soil_query_service.fetch_latest_batch_id()
        business_time = self.service.resolve(
            slots=state.merged_slots,
            latest_business_time=latest_business_time,
            latest_batch_id=latest_batch_id,
            timezone=state.timezone,
        )
        return self.ensure_result(NodeResult(next_action="continue", state_patch={"business_time": business_time}))

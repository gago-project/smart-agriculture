"""Restricted Flow node implementation for soil data query."""

from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.schemas.state import FlowState, NodeResult
from app.services.soil_query_service import SoilQueryService


class SoilDataQueryNode(BaseNode):
    """Flow node for the soil data query stage."""
    def __init__(self, service: SoilQueryService):
        """Initialize the soil data query node."""
        super().__init__("soil_data_query", ("continue", "fallback"), ("query_plan", "query_result", "query_log_entries", "answer_type", "answer_bundle"))
        self.service = service

    async def run(self, state: FlowState) -> NodeResult:
        """Execute the node and return the next flow action."""
        if state.merged_slots.get("region_exists") is False or state.merged_slots.get("device_exists") is False:
            fallback_scenario = "device_exists" if state.merged_slots.get("device_exists") is False else "region_exists"
            query_plan = self.service.build_fallback_query_plan(
                fallback_scenario=fallback_scenario,
                slots=state.merged_slots,
                business_time=state.business_time,
                session_id=state.session_id,
                turn_id=state.turn_id,
                request_id=state.request_id,
            )
            query_result = await self.service.execute(query_plan)
            query_log_entry = self.service.build_query_log_entry(state=state, query_plan=query_plan, query_result=query_result)
            target = state.merged_slots.get("town_name") or state.merged_slots.get("county_name") or state.merged_slots.get("city_name") or state.merged_slots.get("device_sn")
            return self.ensure_result(
                NodeResult(
                    next_action="fallback",
                    state_patch={
                        "query_plan": query_plan,
                        "query_result": query_result,
                        "query_log_entries": [query_log_entry],
                        "answer_type": "fallback_answer",
                        "answer_bundle": {"final_answer": f"没有找到 {target} 的有效墒情数据，请核对名称或设备编号后重试。"},
                    },
                )
            )
        query_plan = self.service.build_query_plan(
            intent=state.intent or "",
            slots=state.merged_slots,
            business_time=state.business_time,
            session_id=state.session_id,
            turn_id=state.turn_id,
            request_id=state.request_id,
        )
        query_result = await self.service.execute(query_plan)
        query_log_entry = self.service.build_query_log_entry(state=state, query_plan=query_plan, query_result=query_result)
        if not query_result.get("records") and state.intent in {"soil_region_query", "soil_device_query", "soil_warning_generation"}:
            fallback_plan = self.service.build_fallback_query_plan(
                fallback_scenario="period_exists",
                slots=state.merged_slots,
                business_time=state.business_time,
                session_id=state.session_id,
                turn_id=state.turn_id,
                request_id=state.request_id,
            )
            fallback_result = await self.service.execute(fallback_plan)
            fallback_log_entry = self.service.build_query_log_entry(state=state, query_plan=fallback_plan, query_result=fallback_result)
            target = state.merged_slots.get("town_name") or state.merged_slots.get("county_name") or state.merged_slots.get("city_name") or state.merged_slots.get("device_sn") or "当前对象"
            latest_time = fallback_result.get("latest_sample_time") or state.business_time.get("latest_business_time") or "暂无"
            return self.ensure_result(
                NodeResult(
                    next_action="fallback",
                    state_patch={
                        "query_plan": fallback_plan,
                        "query_result": fallback_result,
                        "query_log_entries": [query_log_entry, fallback_log_entry],
                        "answer_type": "fallback_answer",
                        "answer_bundle": {"final_answer": f"{target} 在当前查询范围内暂无可用数据。当前库内最新业务时间截至 {latest_time}，请核对名称、时间范围或导入最新数据后再试。"},
                    },
                )
            )
        return self.ensure_result(
            NodeResult(
                next_action="continue",
                state_patch={"query_plan": query_plan, "query_result": query_result, "query_log_entries": [query_log_entry]},
            )
        )

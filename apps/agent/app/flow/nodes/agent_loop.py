"""Flow node wrapping AgentLoopService.

Sets answer_type, output_mode, intent, fallback_reason, tool_trace,
and query_log_entries based on AgentLoopResult.
"""
from __future__ import annotations

from app.flow.nodes.base import BaseNode
from app.repositories.soil_repository import SoilRepository
from app.schemas.state import FlowState, NodeResult
from app.services.agent_loop_service import AgentLoopService

_TOOL_TO_ANSWER_TYPE = {
    "query_soil_summary": "soil_summary_answer",
    "query_soil_ranking": "soil_ranking_answer",
    "query_soil_detail": "soil_detail_answer",
    "diagnose_empty_result": "fallback_answer",
}

_TOOL_TO_INTENT = {
    "query_soil_summary": "soil_recent_summary",
    "query_soil_ranking": "soil_severity_ranking",
    "query_soil_detail": "soil_region_query",
    "diagnose_empty_result": "soil_diagnose",
}


class AgentLoopNode(BaseNode):
    """Run the LLM + function-calling loop and populate final answer."""

    def __init__(self, service: AgentLoopService, *, repository: SoilRepository) -> None:
        super().__init__(
            "agent_loop",
            ("continue", "fallback"),
            ("intent", "answer_type", "output_mode", "fallback_reason",
             "answer_bundle", "query_result", "query_log_entries",
             "tool_trace", "answer_facts"),
        )
        self.service = service
        self.repository = repository

    async def run(self, state: FlowState) -> NodeResult:
        latest_business_time = await self.repository.latest_business_time_async()
        result = await self.service.run(
            user_input=state.user_input,
            session_id=state.session_id,
            turn_id=state.turn_id,
            latest_business_time=latest_business_time,
            is_business_query=True,
        )

        patch: dict = {
            "answer_bundle": {"final_answer": result.final_answer},
        }

        # Derive answer_type and intent from the first successful tool call
        first_tool = result.tool_calls_made[0]["tool_name"] if result.tool_calls_made else None
        if result.is_fallback:
            patch["answer_type"] = "fallback_answer"
            patch["fallback_reason"] = result.fallback_reason or "unknown"
        elif first_tool:
            patch["answer_type"] = _TOOL_TO_ANSWER_TYPE.get(first_tool, "soil_summary_answer")
            patch["intent"] = _TOOL_TO_INTENT.get(first_tool, "soil_recent_summary")
            # Refine intent for detail: device vs region
            if first_tool == "query_soil_detail":
                first_args = result.tool_calls_made[0].get("tool_args", {})
                if first_args.get("sn"):
                    patch["intent"] = "soil_device_query"

        # output_mode from first tool's args
        if result.tool_calls_made:
            first_args = result.tool_calls_made[0].get("tool_args", {})
            output_mode = first_args.get("output_mode")
            if output_mode:
                patch["output_mode"] = output_mode

        # query_result: collect records from tool results (summary/detail may not have 'records')
        records: list = []
        for tool_result in result.tool_results:
            if "records" in tool_result:
                records.extend(tool_result["records"])
            elif "alert_records" in tool_result:
                records.extend(tool_result["alert_records"])
            elif "items" in tool_result:
                records.extend(tool_result["items"])
        patch["query_result"] = {"records": records}

        # tool_trace for evidence chain
        patch["tool_trace"] = [
            {
                "tool_name": tc["tool_name"],
                "tool_args": tc.get("tool_args", {}),
                "result_summary": _summarize_result(tr),
            }
            for tc, tr in zip(result.tool_calls_made, result.tool_results)
        ]

        # answer_facts: structured evidence from tool results
        if result.tool_results:
            patch["answer_facts"] = result.tool_results[0]

        # query_log_entries: one entry per tool call
        patch["query_log_entries"] = [
            {
                "tool_name": tc["tool_name"],
                "tool_args": {k: v for k, v in tc.get("tool_args", {}).items()
                              if k not in ("start_time", "end_time")},
                "time_window": {
                    "start_time": tc.get("tool_args", {}).get("start_time"),
                    "end_time": tc.get("tool_args", {}).get("end_time"),
                },
                "result_summary": _summarize_result(tr),
                "hit": _has_data(tr),
            }
            for tc, tr in zip(result.tool_calls_made, result.tool_results)
        ]

        if result.is_fallback:
            return self.ensure_result(NodeResult(next_action="fallback", state_patch=patch))
        return self.ensure_result(NodeResult(next_action="continue", state_patch=patch))


def _summarize_result(result: dict) -> dict:
    """Return a compact summary of a tool result for the audit log."""
    if "total_records" in result:
        return {
            "total_records": result.get("total_records"),
            "alert_count": result.get("alert_count"),
            "avg_water20cm": result.get("avg_water20cm"),
        }
    if "items" in result:
        return {"item_count": len(result.get("items", [])), "aggregation": result.get("aggregation")}
    if "record_count" in result:
        return {"record_count": result.get("record_count"), "entity_name": result.get("entity_name")}
    if "diagnosis" in result:
        return {"diagnosis": result.get("diagnosis"), "entity_name": result.get("entity_name")}
    return {}


def _has_data(result: dict) -> bool:
    if result.get("total_records", -1) > 0:
        return True
    if result.get("items"):
        return True
    if result.get("record_count", -1) > 0:
        return True
    if result.get("diagnosis") == "data_exists":
        return True
    return False

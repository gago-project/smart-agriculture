"""Flow node wrapping AgentLoopService.

Sets answer_type, output_mode, intent, fallback_reason, tool_trace,
and query_log_entries based on AgentLoopResult.

P1-7/8/9: For business_colloquial inputs, SemanticParserService is called
first to resolve coreferences and extract an explicit intent_hint.
The resolved_input (coreference-expanded) is passed to AgentLoopService.
"""
from __future__ import annotations

import logging
import re

from app.flow.nodes.base import BaseNode
from app.llm.tools import get_tool_meta
from app.repositories.soil_repository import SoilRepository
from app.schemas.state import FlowState, NodeResult
from app.services.agent_loop_service import AgentLoopService
from app.services.semantic_parser_service import SemanticParseResult, SemanticParserService
from app.services.time_window_service import TimeWindowService

logger = logging.getLogger(__name__)

_EXPLICIT_SN_PATTERN = re.compile(r"SNS[\w-]+", re.IGNORECASE)
_SELF_CONTAINED_QUERY_PATTERN = re.compile(r"(查一下|查下|看一下|看下|帮我查一下|帮我看一下).+的情况")

_INTENT_HINT_MAP = {
    "soil_summary": "soil_recent_summary",
    "soil_ranking": "soil_severity_ranking",
    "soil_detail": "soil_region_query",
}


class AgentLoopNode(BaseNode):
    """Run the LLM + function-calling loop and populate final answer."""

    def __init__(
        self,
        service: AgentLoopService,
        *,
        repository: SoilRepository,
        semantic_parser: SemanticParserService | None = None,
    ) -> None:
        super().__init__(
            "agent_loop",
            ("continue", "clarify", "fallback"),
            ("intent", "answer_type", "output_mode", "fallback_reason", "guidance_reason",
             "answer_bundle", "query_result", "query_log_entries",
             "tool_trace", "answer_facts", "session_reset"),
        )
        self.service = service
        self.repository = repository
        self.semantic_parser = semantic_parser or SemanticParserService()
        self.time_window_service = TimeWindowService()

    async def run(self, state: FlowState) -> NodeResult:
        latest_business_time = await self.repository.latest_business_time_async()
        original_time_evidence = self.time_window_service.resolve(state.user_input, latest_business_time)

        # P1-8/9: For colloquial business inputs, resolve coreferences and get intent_hint
        effective_input = state.user_input
        semantic_intent_hint: str | None = None
        semantic_seed_args: dict[str, str] | None = None
        if getattr(state, "input_type", None) and str(state.input_type or "").endswith("colloquial"):
            history = await self.service.history_store.load_history(state.session_id)
            if state.turn_id > 1 and not history:
                patch: dict = {
                    "answer_bundle": {"final_answer": (
                        "上一轮已经结束话题，这一轮我需要重新确认要查的内容。"
                        "请补充时间范围，例如“如东县最近 7 天墒情怎么样”或“如东县当前最新一期情况如何”。"
                    )},
                    "answer_type": "guidance_answer",
                    "guidance_reason": "clarification",
                    "session_reset": True,
                    "answer_facts": {"should_clarify": True, "context_reset_after_closing": True},
                }
                return self.ensure_result(NodeResult(next_action="clarify", state_patch=patch))
            parse_result = await self.semantic_parser.parse(
                state.user_input,
                history,
                latest_business_time=latest_business_time,
            )
            if parse_result.needs_clarify and parse_result.clarify_message:
                if _should_defer_semantic_clarify(parse_result) or _can_bypass_semantic_clarify(state.user_input):
                    parse_result = SemanticParseResult(resolved_input=state.user_input)
                else:
                    patch: dict = {
                        "answer_bundle": {"final_answer": (
                            f"您的问题需要补充一些信息：{parse_result.clarify_message}。"
                            "请补充说明后重试。"
                        )},
                        "answer_type": "guidance_answer",
                        "guidance_reason": "clarification",
                        "session_reset": False,
                    }
                    return self.ensure_result(NodeResult(next_action="clarify", state_patch=patch))
            effective_input = parse_result.resolved_input
            if (
                parse_result.start_time
                and parse_result.end_time
                and not original_time_evidence.has_time_signal
            ):
                # Keep colloquial follow-ups on the original utterance so time inheritance
                # stays owned by the resolver instead of a semantic rewrite.
                effective_input = state.user_input
            semantic_intent_hint = _INTENT_HINT_MAP.get(parse_result.intent_hint)
            if parse_result.entities or parse_result.start_time or parse_result.end_time:
                logger.debug(
                    "SemanticParser resolved: entities=%s start=%s end=%s input=%r",
                    parse_result.entities,
                    parse_result.start_time,
                    parse_result.end_time,
                    effective_input,
                )
            semantic_seed_args = dict(parse_result.entities or {})
            if (
                parse_result.start_time
                and parse_result.end_time
                and original_time_evidence.has_time_signal
            ):
                semantic_seed_args.setdefault("start_time", parse_result.start_time)
                semantic_seed_args.setdefault("end_time", parse_result.end_time)
            if not semantic_seed_args:
                semantic_seed_args = None

        result = await self.service.run(
            user_input=effective_input,
            session_id=state.session_id,
            turn_id=state.turn_id,
            latest_business_time=latest_business_time,
            is_business_query=True,
            semantic_seed_args=semantic_seed_args,
        )

        patch: dict = {
            "answer_bundle": {"final_answer": result.final_answer},
            "session_reset": result.session_reset,
        }
        if result.needs_clarify:
            patch["answer_type"] = "guidance_answer"
            patch["guidance_reason"] = "clarification"
            return self.ensure_result(NodeResult(next_action="clarify", state_patch=patch))

        # Derive answer_type from the final result structure (P1-9)
        # intent: prefer semantic_intent_hint (from SemanticParser); fall back to tool meta
        first_tool = result.tool_calls_made[0]["tool_name"] if result.tool_calls_made else None
        if result.is_fallback:
            patch["answer_type"] = "fallback_answer"
            patch["fallback_reason"] = result.fallback_reason or "unknown"
        elif first_tool:
            # answer_type reflects actual result: has data → tool meta typed answer, else fallback
            has_any_data = any(_has_data(tr) for tr in result.tool_results)
            tool_meta = get_tool_meta(first_tool)
            patch["answer_type"] = (
                tool_meta.get("answer_type", "soil_summary_answer")
                if has_any_data else "fallback_answer"
            )
            if not has_any_data:
                empty_result_path = next(
                    (
                        str(tr.get("empty_result_path") or "")
                        for tr in result.tool_results
                        if isinstance(tr, dict) and tr.get("empty_result_path")
                    ),
                    "",
                )
                fallback_reason = _fallback_reason_from_empty_result_path(empty_result_path)
                if fallback_reason:
                    patch["fallback_reason"] = fallback_reason
            # intent: semantic hint wins; otherwise read from tool meta
            if semantic_intent_hint:
                patch["intent"] = semantic_intent_hint
            else:
                patch["intent"] = tool_meta.get("intent", "soil_recent_summary")
            # Refine detail intent: device vs region (only orthogonal evidence-based override)
            if first_tool == "query_soil_detail":
                first_args = result.tool_calls_made[0].get("tool_args", {})
                if first_args.get("sn"):
                    patch["intent"] = "soil_device_query"

        # output_mode from first tool's args
        if result.tool_calls_made and patch.get("answer_type") != "fallback_answer":
            first_args = result.tool_calls_made[0].get("tool_args", {})
            first_result = result.tool_results[0] if result.tool_results else {}
            output_mode = first_result.get("output_mode") or first_args.get("output_mode")
            if output_mode:
                patch["output_mode"] = output_mode

        # query_result: full structured result from every tool call, keyed by position
        query_results: list[dict] = []
        for tc, tr in zip(result.tool_calls_made, result.tool_results):
            query_results.append({
                "tool_name": tc["tool_name"],
                "tool_args": tc.get("tool_args", {}),
                "result": tr,
            })
        patch["query_result"] = {"entries": query_results}

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
            first_result = dict(result.tool_results[0])
            first_call = result.tool_calls_made[0] if result.tool_calls_made else {}
            if result.tool_calls_made and result.tool_calls_made[0].get("tool_name") == "query_soil_comparison":
                first_result.setdefault("comparison", first_result.get("items") or [])
            if result.tool_calls_made and result.tool_calls_made[0].get("tool_name") == "query_soil_summary":
                tool_args = first_call.get("tool_args", {})
                first_result.setdefault("entity_type", "device" if tool_args.get("sn") else "region")
                first_result.setdefault(
                    "entity_name",
                    tool_args.get("sn") or tool_args.get("county") or tool_args.get("city") or "全局",
                )
            first_result["entity_confidence"] = first_call.get("entity_confidence", result.entity_confidence)
            first_result["used_context"] = bool(first_call.get("used_context"))
            first_result["time_source"] = first_call.get("time_source")
            first_result["context_correction"] = state.user_input.strip().startswith("不是") and "是" in state.user_input
            patch["answer_facts"] = first_result

        patch["query_log_entries"] = result.query_log_entries

        if result.is_fallback:
            return self.ensure_result(NodeResult(next_action="fallback", state_patch=patch))
        return self.ensure_result(NodeResult(next_action="continue", state_patch=patch))


def _summarize_result(result: dict) -> dict:
    """Return a compact summary of a tool result for the audit log."""
    if "total_records" in result:
        return {
            "total_records": result.get("total_records"),
            "device_count": result.get("device_count"),
            "region_count": result.get("region_count"),
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


def _fallback_reason_from_empty_result_path(path: str) -> str | None:
    if path == "entity_not_found":
        return "entity_not_found"
    if path == "no_data_in_window":
        return "no_data"
    if path == "normalize_failed":
        return "entity_not_found"
    return None


def _should_defer_semantic_clarify(parse_result: SemanticParseResult) -> bool:
    if parse_result.intent_hint in _INTENT_HINT_MAP:
        return True
    if parse_result.entities:
        return True
    return bool(parse_result.start_time or parse_result.end_time)


def _can_bypass_semantic_clarify(user_input: str) -> bool:
    compact = "".join((user_input or "").split())
    if _EXPLICIT_SN_PATTERN.search(compact):
        return True
    return bool(_SELF_CONTAINED_QUERY_PATTERN.search(compact))

"""LLM ↔ tool-call loop: the core Agent brain.

P0 contract: business queries MUST hit at least one tool before returning a
final text answer.  If the LLM returns text without calling any tool and
is_business_query=True, the result is treated as a fallback with
fallback_reason="tool_missing".

Each request:
1. Load conversation history from Redis
2. Build messages = system_prompt + history + user message
3. LLM call → tool_call or text
4. If tool_call: validate + execute → append standard tool transcript → loop
5. If text AND (not is_business_query OR tool was called): that is the final answer
6. Save full turn (user/assistant/tool messages) to history
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.llm.qwen_client import QwenClient
from app.llm.prompts.system_prompt import build_system_prompt
from app.llm.tools import get_tool_meta, get_tools_for_llm
from app.repositories.session_context_repository import SessionContextRepository
from app.services.parameter_resolver_service import ParameterResolverService
from app.services.time_window_service import TimeWindowService
from app.services.tool_executor_service import ToolExecutorService, ToolValidationError

MAX_TOOL_ITERATIONS = 5
_FALLBACK_NO_LLM = "LLM 服务当前不可用，请稍后重试或联系管理员配置 API Key。"
_FALLBACK_MAX_ITER = "当前请求调用工具次数过多，已安全终止，请缩小问题范围后重试。"
_FALLBACK_TOOL_MISSING = (
    "当前业务问题必须查询真实数据后才能回答。"
    "系统检测到模型未调用任何查询工具就直接作答，已拦截此回答，请换一种问法重试。"
)


@dataclass
class AgentLoopResult:
    """Result returned by one agent loop execution."""
    final_answer: str
    tool_calls_made: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    query_log_entries: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    is_fallback: bool = False
    fallback_reason: str = "unknown"
    # Resolver audit fields (populated per tool call)
    entity_confidence: str = "high"
    time_confidence: str = "high"
    resolver_warnings: list[str] = field(default_factory=list)
    needs_clarify: bool = False
    # TTL awareness: True when turn_id > 1 but history was empty (session expired)
    session_reset: bool = False


class AgentLoopService:
    """Execute the LLM ↔ tool-call loop for one user turn."""

    def __init__(
        self,
        *,
        qwen_client: QwenClient,
        tool_executor: ToolExecutorService,
        history_store: SessionContextRepository,
        resolver: ParameterResolverService | None = None,
        time_window_service: TimeWindowService | None = None,
    ) -> None:
        self.qwen_client = qwen_client
        self.tool_executor = tool_executor
        self.history_store = history_store
        self.resolver = resolver or ParameterResolverService()
        self.time_window_service = time_window_service or TimeWindowService()

    async def run(
        self,
        *,
        user_input: str,
        session_id: str,
        turn_id: int,
        latest_business_time: str | None,
        is_business_query: bool = True,
    ) -> AgentLoopResult:
        """Run the agent loop and return the final answer with execution trace.

        is_business_query=True means at least one tool call is required before
        accepting a text answer.  InputGuardNode always passes True here.
        """
        if not self.qwen_client.available():
            return AgentLoopResult(
                final_answer=_FALLBACK_NO_LLM,
                is_fallback=True,
                fallback_reason="tool_missing",
            )

        history = await self.history_store.load_history(session_id)
        # Detect TTL expiry: user is continuing a conversation but context is gone
        session_reset = turn_id > 1 and len(history) == 0
        inherited_time_window = self._latest_history_time_window(history)
        time_evidence = self.time_window_service.resolve(user_input, latest_business_time)
        system_prompt = build_system_prompt(latest_business_time=latest_business_time)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_input},
        ]

        tool_calls_made: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        history_tool_calls: list[dict[str, Any]] = []
        history_tool_results: list[dict[str, Any]] = []
        query_log_entries: list[dict[str, Any]] = []
        all_resolver_warnings: list[str] = []
        last_entity_confidence = "high"
        last_time_confidence = "high"

        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self.qwen_client.call_with_tools(
                messages=messages,
                tools=get_tools_for_llm(),
            )
            if response is None:
                return AgentLoopResult(
                    final_answer=_FALLBACK_NO_LLM,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results,
                    messages=messages,
                    is_fallback=True,
                    fallback_reason="tool_missing",
                    session_reset=session_reset,
                )

            if response["type"] == "text":
                final_answer = response["content"]

                # P0: business query must have called at least one tool
                if is_business_query and not tool_calls_made:
                    await self.history_store.save_message_turn(
                        session_id, turn_id,
                        user_message=user_input,
                        assistant_message=_FALLBACK_TOOL_MISSING,
                        tool_calls=history_tool_calls,
                        tool_results=history_tool_results,
                    )
                    return AgentLoopResult(
                        final_answer=_FALLBACK_TOOL_MISSING,
                        tool_calls_made=tool_calls_made,
                        tool_results=tool_results,
                        query_log_entries=query_log_entries,
                        messages=messages,
                        is_fallback=True,
                        fallback_reason="tool_missing",
                        session_reset=session_reset,
                    )

                await self.history_store.save_message_turn(
                    session_id, turn_id,
                    user_message=user_input,
                    assistant_message=final_answer,
                    tool_calls=history_tool_calls,
                    tool_results=history_tool_results,
                )
                return AgentLoopResult(
                    final_answer=final_answer,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results,
                    query_log_entries=query_log_entries,
                    messages=messages,
                    is_fallback=False,
                    fallback_reason="",
                    entity_confidence=last_entity_confidence,
                    time_confidence=last_time_confidence,
                    resolver_warnings=all_resolver_warnings,
                    session_reset=session_reset,
                )

            # tool_calls branch — process the full batch returned by the model
            batch = response.get("calls") or []
            batch_tool_calls: list[dict] = []  # assistant tool-call entries for this batch

            clarify_triggered = False
            clarify_answer = ""

            for call in batch:
                tool_name = call["tool_name"]
                raw_args = call["tool_args"]
                call_id = call.get("call_id", "")

                # --- Parameter Resolver ---
                resolved = await self.resolver.resolve(
                    tool_name,
                    raw_args,
                    latest_business_time,
                    user_input=user_input,
                    time_evidence=time_evidence,
                    inherited_time_window=inherited_time_window,
                )
                last_entity_confidence = resolved.entity_confidence
                last_time_confidence = resolved.time_confidence
                all_resolver_warnings.extend(resolved.warning_trace)

                if resolved.should_clarify:
                    clarify_triggered = True
                    clarify_answer = (
                        f"您的问题中有些信息需要确认：{resolved.clarify_message}。"
                        "请补充说明后重试。"
                    )
                    break

                tool_args = resolved.resolved_args

                assistant_tool_call = self._standard_tool_call(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    call_id=call_id,
                )
                batch_tool_calls.append(assistant_tool_call)

                try:
                    result = await self.tool_executor.execute(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        entity_confidence=resolved.entity_confidence,
                    )
                    query_log_entry = self._build_query_log_entry(
                        session_id=session_id,
                        turn_id=turn_id,
                        tool_index=len(query_log_entries),
                        tool_name=tool_name,
                        raw_args=raw_args,
                        resolved_args=tool_args,
                        result=result,
                        resolved=resolved,
                    )
                    query_log_entries.append(query_log_entry)
                    tool_calls_made.append({
                        "tool_name": tool_name,
                        "raw_args": raw_args,
                        "tool_args": tool_args,
                        "call_id": call_id,
                        "entity_confidence": resolved.entity_confidence,
                        "time_confidence": resolved.time_confidence,
                        "resolver_warnings": resolved.warning_trace,
                        "time_source": resolved.time_source,
                        "used_context": bool(query_log_entry.get("used_context")),
                    })
                    tool_results.append(result)
                    history_tool_results.append(result)
                    tool_content = json.dumps(result, ensure_ascii=False, default=str)
                except ToolValidationError as exc:
                    if self._is_time_validation_error(str(exc)):
                        clarify_triggered = True
                        clarify_answer = (
                            "您的问题中有些信息需要确认："
                            "你想查看的时间段是？例如 最近 7 天、上周、2026 年 4 月、4 月 1 日到 4 月 13 日。"
                            "请补充说明后重试。"
                        )
                        break
                    # Validation failure short-circuits the whole batch
                    error_result = {"error": str(exc)}
                    history_tool_results.append(error_result)
                    tool_content = json.dumps(error_result, ensure_ascii=False)
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [assistant_tool_call],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_content,
                    })
                    history_tool_calls.extend(batch_tool_calls)
                    break

                messages_tool_entry = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_content,
                }
                # Defer appending until after the loop so the assistant message comes first
                call["_tool_msg"] = messages_tool_entry

            if clarify_triggered:
                await self.history_store.save_message_turn(
                    session_id, turn_id,
                    user_message=user_input,
                    assistant_message=clarify_answer,
                    tool_calls=history_tool_calls,
                    tool_results=history_tool_results,
                )
                return AgentLoopResult(
                    final_answer=clarify_answer,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results,
                    query_log_entries=query_log_entries,
                    messages=messages,
                    is_fallback=False,
                    fallback_reason="",
                    entity_confidence=last_entity_confidence,
                    time_confidence=last_time_confidence,
                    resolver_warnings=all_resolver_warnings,
                    needs_clarify=True,
                    session_reset=session_reset,
                )

            # Append all batch messages: single assistant message with full tool_calls list, then tool results
            if batch_tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": batch_tool_calls,
                })
                history_tool_calls.extend(batch_tool_calls)
                for call in batch:
                    if "_tool_msg" in call:
                        messages.append(call["_tool_msg"])

        # Exceeded MAX_TOOL_ITERATIONS
        await self.history_store.save_message_turn(
            session_id, turn_id,
            user_message=user_input,
            assistant_message=_FALLBACK_MAX_ITER,
            tool_calls=history_tool_calls,
            tool_results=history_tool_results,
        )
        return AgentLoopResult(
            final_answer=_FALLBACK_MAX_ITER,
            tool_calls_made=tool_calls_made,
            tool_results=tool_results,
            query_log_entries=query_log_entries,
            messages=messages,
            is_fallback=True,
            fallback_reason="tool_blocked",
            session_reset=session_reset,
        )

    def _build_query_log_entry(
        self,
        *,
        session_id: str,
        turn_id: int,
        tool_index: int,
        tool_name: str,
        raw_args: dict[str, Any],
        resolved_args: dict[str, Any],
        result: dict[str, Any],
        resolved,
    ) -> dict[str, Any]:
        meta = get_tool_meta(tool_name)
        query_type = self._query_type_for_tool(tool_name, resolved_args)
        row_count = self._row_count_for_result(result)
        time_range = {
            "start_time": resolved_args.get("start_time"),
            "end_time": resolved_args.get("end_time"),
            "time_source": resolved.time_source,
            "inherited": resolved.time_source == "history_inherited",
        }
        query_plan = {
            "tool_name": tool_name,
            "intent": meta.get("intent", ""),
            "answer_type": meta.get("answer_type", ""),
            "output_mode": resolved_args.get("output_mode"),
            "aggregation": resolved_args.get("aggregation"),
            "entity_type": resolved_args.get("entity_type"),
            "top_n": resolved_args.get("top_n"),
            "resolver_warnings": list(resolved.warning_trace),
        }
        filters = {
            key: resolved_args.get(key)
            for key in ("city", "county", "sn", "entities", "entity_type")
            if resolved_args.get(key) is not None
        }
        return {
            "query_id": f"{session_id}:{turn_id}:{tool_index}",
            "session_id": session_id,
            "turn_id": turn_id,
            "query_type": query_type,
            "query_plan_json": query_plan,
            "sql_fingerprint": query_type,
            "executed_sql_text": self._build_audit_sql_for_tool(tool_name, resolved_args),
            "time_range_json": time_range,
            "filters_json": filters,
            "raw_args_json": dict(raw_args),
            "resolved_args_json": dict(resolved_args),
            "entity_confidence": resolved.entity_confidence,
            "time_confidence": resolved.time_confidence,
            "rule_version": result.get("rule_version"),
            "empty_result_path": result.get("empty_result_path"),
            "group_by_json": self._group_by_for_tool(tool_name, resolved_args),
            "metrics_json": self._metrics_for_tool(tool_name),
            "order_by_json": self._order_by_for_tool(tool_name, resolved_args),
            "limit_size": self._limit_for_tool(tool_name, resolved_args),
            "row_count": row_count,
            "executed_result_json": result,
            "source_files_json": None,
            "status": "empty" if row_count == 0 else "success",
            "error_message": None,
            "resolver_warnings": list(resolved.warning_trace),
            "time_source": resolved.time_source,
            "used_context": resolved.time_source == "history_inherited",
        }

    @staticmethod
    def _latest_history_time_window(history: list[dict[str, Any]]) -> dict[str, str] | None:
        for message in reversed(history):
            tool_calls = message.get("tool_calls") or []
            for tool_call in reversed(tool_calls):
                function = (tool_call or {}).get("function") or {}
                arguments = function.get("arguments")
                try:
                    args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
                except Exception:
                    continue
                start_time = args.get("start_time")
                end_time = args.get("end_time")
                if start_time and end_time:
                    return {"start_time": str(start_time), "end_time": str(end_time)}
        return None

    @staticmethod
    def _is_time_validation_error(message: str) -> bool:
        normalized = message.lower()
        return any(token in normalized for token in ("start_time", "end_time", "time_span"))

    @staticmethod
    def _standard_tool_call(*, tool_name: str, tool_args: dict[str, Any], call_id: str) -> dict[str, Any]:
        """Return the canonical assistant.tool_calls entry stored in history."""
        return {
            "id": call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(tool_args, ensure_ascii=False),
            },
        }

    @staticmethod
    def _row_count_for_result(result: dict[str, Any]) -> int:
        if "total_records" in result:
            return int(result.get("total_records") or 0)
        if "record_count" in result:
            return int(result.get("record_count") or 0)
        if "items" in result:
            return len(result.get("items") or [])
        if "comparisons" in result:
            return len(result.get("comparisons") or [])
        if "total_entities" in result:
            return int(result.get("total_entities") or 0)
        return 0

    def _build_audit_sql_for_tool(self, tool_name: str, resolved_args: dict[str, Any]) -> str | None:
        repository = getattr(self.tool_executor, "repository", None)
        render = getattr(repository, "build_filter_records_audit_sql", None)
        if not callable(render):
            return None

        if tool_name == "query_soil_comparison":
            entities = resolved_args.get("entities")
            if not isinstance(entities, list) or not entities:
                return None
            sql_blocks: list[str] = []
            for index, entity in enumerate(entities, start=1):
                if not isinstance(entity, dict):
                    continue
                filters = self._comparison_entity_filters(entity)
                if not filters:
                    continue
                label = str(entity.get("canonical_name") or entity.get("raw_name") or f"entity_{index}")
                level = str(entity.get("level") or "region")
                sql_blocks.append(
                    "\n".join(
                        [
                            f"-- entity {index}: {label} ({level})",
                            render(
                                start_time=resolved_args.get("start_time"),
                                end_time=resolved_args.get("end_time"),
                                **filters,
                            ),
                        ]
                    )
                )
            return "\n\n".join(sql_blocks) if sql_blocks else None

        return render(
            city=resolved_args.get("city"),
            county=resolved_args.get("county"),
            sn=resolved_args.get("sn"),
            start_time=resolved_args.get("start_time"),
            end_time=resolved_args.get("end_time"),
        )

    @staticmethod
    def _comparison_entity_filters(entity: dict[str, Any]) -> dict[str, Any]:
        canonical_name = entity.get("canonical_name")
        level = entity.get("level")
        if not canonical_name:
            return {}
        if level == "device":
            return {"sn": canonical_name}
        if level == "city":
            return {"city": canonical_name}
        if level == "county":
            return {"county": canonical_name}
        return {}

    @staticmethod
    def _query_type_for_tool(tool_name: str, resolved_args: dict[str, Any]) -> str:
        if tool_name == "query_soil_summary":
            return "recent_summary"
        if tool_name == "query_soil_ranking":
            return "severity_ranking"
        if tool_name == "query_soil_detail":
            return "device_detail" if resolved_args.get("sn") else "region_detail"
        if tool_name == "query_soil_comparison":
            return "comparison"
        if tool_name == "diagnose_empty_result":
            return "fallback"
        return tool_name

    @staticmethod
    def _group_by_for_tool(tool_name: str, resolved_args: dict[str, Any]) -> list[str] | None:
        if tool_name == "query_soil_ranking":
            return [str(resolved_args.get("aggregation") or "county")]
        if tool_name == "query_soil_comparison":
            return [str(resolved_args.get("entity_type") or "region")]
        return None

    @staticmethod
    def _metrics_for_tool(tool_name: str) -> list[str]:
        if tool_name == "query_soil_summary":
            return ["total_records", "avg_water20cm", "alert_count"]
        if tool_name == "query_soil_ranking":
            return ["avg_risk_score", "alert_count", "record_count"]
        if tool_name == "query_soil_detail":
            return ["record_count", "status_summary"]
        if tool_name == "query_soil_comparison":
            return ["avg_risk_score", "alert_count", "record_count"]
        return []

    @staticmethod
    def _order_by_for_tool(tool_name: str, resolved_args: dict[str, Any]) -> list[str] | None:
        if tool_name in {"query_soil_ranking", "query_soil_comparison"}:
            return ["avg_risk_score DESC", "alert_count DESC", f"limit={resolved_args.get('top_n') or 5}"]
        return None

    @staticmethod
    def _limit_for_tool(tool_name: str, resolved_args: dict[str, Any]) -> int | None:
        if tool_name == "query_soil_ranking":
            return int(resolved_args.get("top_n") or 5)
        if tool_name == "query_soil_comparison":
            entities = resolved_args.get("entities")
            return len(entities) if isinstance(entities, list) else None
        return None


__all__ = ["AgentLoopService", "AgentLoopResult"]

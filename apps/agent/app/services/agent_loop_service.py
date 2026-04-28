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
from app.llm.tools import get_tools_for_llm
from app.repositories.session_context_repository import SessionContextRepository
from app.services.parameter_resolver_service import ParameterResolverService
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
    messages: list[dict[str, Any]] = field(default_factory=list)
    is_fallback: bool = False
    fallback_reason: str = "unknown"
    # Resolver audit fields (populated per tool call)
    entity_confidence: str = "high"
    time_confidence: str = "high"
    resolver_warnings: list[str] = field(default_factory=list)
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
    ) -> None:
        self.qwen_client = qwen_client
        self.tool_executor = tool_executor
        self.history_store = history_store
        self.resolver = resolver or ParameterResolverService()

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
                    tool_name, raw_args, latest_business_time
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
                    tool_args=raw_args,
                    call_id=call_id,
                )
                batch_tool_calls.append(assistant_tool_call)

                try:
                    result = await self.tool_executor.execute(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        entity_confidence=resolved.entity_confidence,
                    )
                    tool_calls_made.append({
                        "tool_name": tool_name,
                        "raw_args": raw_args,
                        "tool_args": tool_args,
                        "call_id": call_id,
                        "entity_confidence": resolved.entity_confidence,
                        "time_confidence": resolved.time_confidence,
                        "resolver_warnings": resolved.warning_trace,
                    })
                    tool_results.append(result)
                    history_tool_results.append(result)
                    tool_content = json.dumps(result, ensure_ascii=False, default=str)
                except ToolValidationError as exc:
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
                    messages=messages,
                    is_fallback=False,
                    fallback_reason="",
                    entity_confidence=last_entity_confidence,
                    time_confidence=last_time_confidence,
                    resolver_warnings=all_resolver_warnings,
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
            messages=messages,
            is_fallback=True,
            fallback_reason="tool_blocked",
            session_reset=session_reset,
        )

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


__all__ = ["AgentLoopService", "AgentLoopResult"]

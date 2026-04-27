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
from app.llm.tools import SOIL_TOOLS
from app.repositories.session_context_repository import SessionContextRepository
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


class AgentLoopService:
    """Execute the LLM ↔ tool-call loop for one user turn."""

    def __init__(
        self,
        *,
        qwen_client: QwenClient,
        tool_executor: ToolExecutorService,
        history_store: SessionContextRepository,
    ) -> None:
        self.qwen_client = qwen_client
        self.tool_executor = tool_executor
        self.history_store = history_store

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

        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self.qwen_client.call_with_tools(
                messages=messages,
                tools=SOIL_TOOLS,
            )
            if response is None:
                return AgentLoopResult(
                    final_answer=_FALLBACK_NO_LLM,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results,
                    messages=messages,
                    is_fallback=True,
                    fallback_reason="tool_missing",
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
                )

            # tool_call branch
            tool_name = response["tool_name"]
            tool_args = response["tool_args"]
            call_id = response.get("call_id", "")

            # Append standard assistant tool-call message
            assistant_tool_call = self._standard_tool_call(
                tool_name=tool_name,
                tool_args=tool_args,
                call_id=call_id,
            )
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [assistant_tool_call],
            })
            history_tool_calls.append(assistant_tool_call)

            try:
                result = await self.tool_executor.execute(tool_name=tool_name, tool_args=tool_args)
                tool_calls_made.append({"tool_name": tool_name, "tool_args": tool_args, "call_id": call_id})
                tool_results.append(result)
                history_tool_results.append(result)
                tool_content = json.dumps(result, ensure_ascii=False, default=str)
            except ToolValidationError as exc:
                error_result = {"error": str(exc)}
                history_tool_results.append(error_result)
                tool_content = json.dumps(error_result, ensure_ascii=False)

            # Append standard tool result message
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_content,
            })

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

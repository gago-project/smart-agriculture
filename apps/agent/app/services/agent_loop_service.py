"""LLM ↔ tool-call loop: the core Agent brain.

Each request:
1. Load conversation history from Redis
2. Build messages = system_prompt + history + user message
3. LLM call → tool_call or text
4. If tool_call: validate + execute → append tool result → loop
5. If text: that is the final answer
6. Save turn to history
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


@dataclass
class AgentLoopResult:
    """Result returned by one agent loop execution."""
    final_answer: str
    tool_calls_made: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    is_fallback: bool = False


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
    ) -> AgentLoopResult:
        """Run the agent loop and return the final answer with execution trace."""
        if not self.qwen_client.available():
            return AgentLoopResult(final_answer=_FALLBACK_NO_LLM, is_fallback=True)

        history = await self.history_store.load_history(session_id)
        system_prompt = build_system_prompt(latest_business_time=latest_business_time)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_input},
        ]

        tool_calls_made: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []

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
                )

            if response["type"] == "text":
                final_answer = response["content"]
                await self.history_store.save_message_turn(
                    session_id, turn_id,
                    user_message=user_input,
                    assistant_message=final_answer,
                    tool_calls=tool_calls_made,
                    tool_results=tool_results,
                )
                return AgentLoopResult(
                    final_answer=final_answer,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results,
                    messages=messages,
                )

            tool_name = response["tool_name"]
            tool_args = response["tool_args"]
            call_id = response.get("call_id", "")

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": call_id, "type": "function",
                                 "function": {"name": tool_name,
                                              "arguments": json.dumps(tool_args, ensure_ascii=False)}}],
            })

            try:
                result = await self.tool_executor.execute(tool_name=tool_name, tool_args=tool_args)
                tool_calls_made.append({"tool_name": tool_name, "tool_args": tool_args})
                tool_results.append(result)
                tool_content = json.dumps(result, ensure_ascii=False, default=str)
            except ToolValidationError as exc:
                tool_content = json.dumps({"error": str(exc)}, ensure_ascii=False)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_content,
            })

        final_answer = _FALLBACK_MAX_ITER
        await self.history_store.save_message_turn(
            session_id, turn_id,
            user_message=user_input,
            assistant_message=final_answer,
            tool_calls=tool_calls_made,
            tool_results=tool_results,
        )
        return AgentLoopResult(
            final_answer=final_answer,
            tool_calls_made=tool_calls_made,
            tool_results=tool_results,
            messages=messages,
            is_fallback=True,
        )


__all__ = ["AgentLoopService", "AgentLoopResult"]

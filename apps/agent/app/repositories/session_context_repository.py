"""Redis-backed conversation message history.

Stores actual user/assistant message pairs (with tool calls and results)
so the LLM agent receives full conversation context each turn.
Previous slot-based storage is replaced; the LLM resolves multi-turn
context natively from message history.

P1-12: Two-step context strategy.
  Step 1 (token sliding window): truncate by token count, not message count.
  Step 2 (structured summarization): when oldest messages must be dropped,
  extract entities / time windows / record counts into a single summary
  system message kept at the head of the transcript. Done deterministically
  (no extra LLM call) so latency stays bounded.
"""
from __future__ import annotations

from datetime import date, datetime
import json
from decimal import Decimal
from typing import Any


_MAX_CONTEXT_TOKENS = 8000
_MIN_MESSAGES_KEEP = 4  # always keep at least the last 2 user+assistant turns
_SUMMARY_PREFIX = "[历史摘要] "  # system message marker for compressed history


def _json_default(value: Any) -> Any:
    """Convert database-native scalar types into JSON-safe primitives."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_dumps(value: Any) -> str:
    """Serialize history payloads with support for Decimal/date values."""
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _estimate_tokens(messages: list) -> int:
    """Rough token count: len(serialized JSON) / 2 handles mixed Chinese/English."""
    return len(_json_dumps(messages)) // 2


def _is_summary_message(msg: dict) -> bool:
    """Return True if the message is the running structured summary."""
    return (
        isinstance(msg, dict)
        and msg.get("role") == "system"
        and isinstance(msg.get("content"), str)
        and msg["content"].startswith(_SUMMARY_PREFIX)
    )


def _parse_summary(msg: dict) -> dict[str, Any]:
    """Extract the structured fields from a previously-rendered summary message."""
    if not _is_summary_message(msg):
        return _empty_summary()
    content = msg["content"][len(_SUMMARY_PREFIX):]
    state = _empty_summary()
    # Each entry like
    # "实体=南通市,如东县;时间窗=2026-04-01 00:00:00~2026-04-13 23:59:59|...;记录=12;问题=..."
    for part in content.split(";"):
        if "=" not in part:
            continue
        key, _, val = part.partition("=")
        key = key.strip()
        val = val.strip()
        if key == "实体" and val:
            state["entities"] = [e for e in val.split(",") if e]
        elif key == "时间窗" and val:
            windows: list[dict[str, str]] = []
            for token in val.split("|"):
                parsed = _parse_time_window_token(token)
                if parsed:
                    windows.append(parsed)
            state["time_windows"] = windows
        elif key == "记录" and val.isdigit():
            state["total_records"] = int(val)
        elif key == "问题" and val:
            state["user_questions"] = [q for q in val.split("|") if q]
    return state


def _empty_summary() -> dict[str, Any]:
    return {
        "entities": [],
        "time_windows": [],
        "total_records": 0,
        "user_questions": [],
    }


def _parse_time_window_token(token: str) -> dict[str, str] | None:
    raw = token.strip()
    if not raw or "~" not in raw:
        return None
    start_time, _, end_time = raw.partition("~")
    start_time = start_time.strip()
    end_time = end_time.strip()
    if not start_time or not end_time:
        return None
    return {"start_time": start_time, "end_time": end_time}


def _render_time_window_token(window: dict[str, Any]) -> str:
    start_time = str(window.get("start_time") or "").strip()
    end_time = str(window.get("end_time") or "").strip()
    if not start_time or not end_time:
        return ""
    return f"{start_time}~{end_time}"


def _merge_summary(base: dict[str, Any], to_drop: list[dict]) -> dict[str, Any]:
    """Fold information from the messages being dropped into a running summary.

    Extraction is deterministic — no LLM. Captures:
      - user message texts (most recent-first window of 5)
      - tool args city/county/sn → entity names
      - tool args start_time + end_time → time windows
      - tool result total_records / record_count → record totals
    """
    merged = {
        "entities": list(base["entities"]),
        "time_windows": list(base["time_windows"]),
        "total_records": int(base["total_records"]),
        "user_questions": list(base["user_questions"]),
    }

    for msg in to_drop:
        role = msg.get("role")
        if role == "user" and isinstance(msg.get("content"), str):
            q = msg["content"].strip()
            if q and q not in merged["user_questions"]:
                merged["user_questions"].append(q)

        elif role == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"] or []:
                fn = (tc or {}).get("function") or {}
                args_raw = fn.get("arguments")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                except Exception:
                    args = {}
                for key in ("city", "county", "sn"):
                    val = args.get(key)
                    if val and val not in merged["entities"]:
                        merged["entities"].append(str(val))
                entities_list = args.get("entities") or []
                if isinstance(entities_list, list):
                    for e in entities_list:
                        if e and e not in merged["entities"]:
                            merged["entities"].append(str(e))
                start_time = args.get("start_time")
                end_time = args.get("end_time")
                if start_time and end_time:
                    window = {"start_time": str(start_time), "end_time": str(end_time)}
                    if window not in merged["time_windows"]:
                        merged["time_windows"].append(window)

        elif role == "tool" and isinstance(msg.get("content"), str):
            try:
                payload = json.loads(msg["content"])
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            for key in ("total_records", "record_count"):
                val = payload.get(key)
                if isinstance(val, int) and val > 0:
                    merged["total_records"] += val
            entity_name = payload.get("entity_name")
            if isinstance(entity_name, str) and entity_name and entity_name not in merged["entities"]:
                merged["entities"].append(entity_name)

    # Cap unbounded growth
    merged["entities"] = merged["entities"][-15:]
    merged["time_windows"] = merged["time_windows"][-8:]
    merged["user_questions"] = merged["user_questions"][-5:]
    return merged


def _render_summary_message(summary: dict[str, Any]) -> dict[str, Any]:
    """Render the running summary back into a system-role message."""
    parts: list[str] = []
    if summary["entities"]:
        parts.append(f"实体={','.join(summary['entities'])}")
    if summary["time_windows"]:
        rendered_windows = [
            token
            for token in (_render_time_window_token(window) for window in summary["time_windows"])
            if token
        ]
        if rendered_windows:
            parts.append(f"时间窗={'|'.join(rendered_windows)}")
    if summary["total_records"] > 0:
        parts.append(f"记录={summary['total_records']}")
    if summary["user_questions"]:
        parts.append(f"问题={'|'.join(summary['user_questions'])}")
    body = ";".join(parts) if parts else "（无）"
    return {"role": "system", "content": f"{_SUMMARY_PREFIX}{body}"}


def _trim_to_token_limit(messages: list) -> list:
    """Compress oldest messages into a head summary until within token budget.

    Algorithm:
      1. If the very first message is an existing summary, peel it off as
         current summary state; otherwise start with an empty summary.
      2. While token budget exceeded AND we still have more than
         _MIN_MESSAGES_KEEP messages: pop the oldest non-kept message,
         merge its information into the running summary.
      3. Re-emit [summary_message, ...remaining messages].

    A summary is only emitted when at least one message has been compressed
    OR a previous summary already existed; otherwise the messages are returned
    unchanged so simple short transcripts have no summary noise.
    """
    if not messages:
        return messages

    # Peel off existing summary if present
    summary_state = _empty_summary()
    has_summary = False
    if _is_summary_message(messages[0]):
        summary_state = _parse_summary(messages[0])
        messages = messages[1:]
        has_summary = True

    dropped: list[dict] = []
    while (
        len(messages) > _MIN_MESSAGES_KEEP
        and _estimate_tokens(
            ([_render_summary_message(summary_state)] if (has_summary or dropped) else [])
            + messages
        ) > _MAX_CONTEXT_TOKENS
    ):
        oldest = messages[0]
        dropped.append(oldest)
        messages = messages[1:]

    if dropped:
        summary_state = _merge_summary(summary_state, dropped)
        has_summary = True

    if has_summary:
        return [_render_summary_message(summary_state), *messages]
    return messages


class InMemoryRedisClient:
    """Async Redis-like in-memory client for tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        del ex
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


class SessionContextRepository:
    """Persist and load conversation message history for one chat session."""

    def __init__(self, redis_client=None, ttl_seconds: int = 7200) -> None:
        self.redis_client = redis_client or InMemoryRedisClient()
        self.ttl_seconds = ttl_seconds

    async def load_history(self, session_id: str) -> list[dict[str, Any]]:
        """Return all stored messages for a session in chronological order."""
        try:
            raw = await self.redis_client.get(self._key(session_id))
        except Exception:
            return []
        if not raw:
            return []
        return json.loads(raw).get("messages", [])

    async def save_message_turn(
        self,
        session_id: str,
        turn_id: int,
        *,
        user_message: str,
        assistant_message: str,
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> None:
        """Append one user+assistant turn using the standard OpenAI transcript format.

        The stored chain is:
          user → assistant(tool_calls) → tool(result) ... → assistant(final_text)
        """
        key = self._key(session_id)
        try:
            raw = await self.redis_client.get(key)
        except Exception:
            return
        messages: list[dict[str, Any]] = json.loads(raw).get("messages", []) if raw else []

        messages.append({"role": "user", "content": user_message})

        if tool_calls:
            # First assistant message: carries tool_calls, no final text yet
            messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
            # One tool result message per call
            for tc, tr in zip(tool_calls, tool_results):
                call_id = tc.get("id", "")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": _json_dumps(tr),
                })

        # Final assistant message with the visible answer text
        messages.append({"role": "assistant", "content": assistant_message})

        messages = _trim_to_token_limit(messages)
        try:
            await self.redis_client.set(
                key,
                _json_dumps({"messages": messages}),
                ex=self.ttl_seconds,
            )
        except Exception:
            return

    async def clear_context(self, session_id: str) -> None:
        """Clear all message history for a session."""
        try:
            await self.redis_client.delete(self._key(session_id))
        except Exception:
            return

    def _key(self, session_id: str) -> str:
        return f"session_msg:{session_id}"


__all__ = [
    "SessionContextRepository",
    "InMemoryRedisClient",
    "_trim_to_token_limit",
    "_render_summary_message",
    "_parse_summary",
]

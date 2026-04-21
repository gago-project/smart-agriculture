from __future__ import annotations


def build_intent_slot_prompt(user_input: str, session_id: str) -> str:
    return f"session_id={session_id}\nuser_input={user_input}"

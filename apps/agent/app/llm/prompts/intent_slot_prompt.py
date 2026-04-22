"""Prompt builders for intent slot prompt within the soil agent."""

from __future__ import annotations


def build_intent_slot_prompt(user_input: str, session_id: str) -> str:
    """Build the structured intent-and-slot extraction prompt."""
    return f"session_id={session_id}\nuser_input={user_input}"

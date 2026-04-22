"""Prompt builders for response prompt within the soil agent."""

from __future__ import annotations

import json
from typing import Any


def build_response_prompt(*, answer_type: str, facts: dict[str, Any], fallback_answer: str) -> str:
    """Build the controlled response-generation prompt."""
    return json.dumps(
        {
            "answer_type": answer_type,
            "facts": facts,
            "fallback_answer": fallback_answer,
        },
        ensure_ascii=False,
    )

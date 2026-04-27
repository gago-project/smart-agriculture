"""Simplified static route table for the LLM + Function Calling Agent.

Five nodes replace the previous eighteen. LLM handles understanding and
tool routing; code handles validation, execution, and safety checks.
"""
from __future__ import annotations

ROUTES = {
    "input_guard": {
        "safe_end": "safe_end",
        "clarify_end": "clarify_end",
        "boundary_end": "boundary_end",
        "closing_end": "closing_end",
        "continue": "agent_loop",
    },
    "agent_loop": {
        "continue": "data_fact_check",
        "fallback": "fallback_guard",
    },
    "data_fact_check": {
        "retry_response": "fallback_guard",
        "go_verify": "answer_verify",
        "fallback": "fallback_guard",
    },
    "answer_verify": {
        "verified_end": "verified_end",
        "fallback": "fallback_guard",
    },
    "fallback_guard": {
        "fallback_end": "fallback_end",
    },
}

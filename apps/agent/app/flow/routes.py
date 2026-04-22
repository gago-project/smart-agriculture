"""Static route table for the restricted Soil Agent Flow.

The design goal is predictability: nodes choose from declared actions, and this
table maps those actions to the next node or terminal.  We intentionally avoid
LLM-generated dynamic graphs here because this project is a data-task agent,
not an open-ended autonomous agent.
"""

from __future__ import annotations


# Terminal actions end the request without visiting another node.  Non-terminal
# actions keep the request on the fixed pipeline: guard -> parse -> context ->
# time -> region -> gate -> query -> rules -> answer -> fact check -> verify.
ROUTES = {
    "input_guard": {
        "safe_end": "safe_end",
        "clarify_end": "clarify_end",
        "boundary_end": "boundary_end",
        "continue": "intent_slot_extract",
    },
    "intent_slot_extract": {"continue": "history_context_merge"},
    "history_context_merge": {"continue": "time_resolve"},
    "time_resolve": {"continue": "region_resolve"},
    "region_resolve": {"continue": "execution_gate"},
    "execution_gate": {
        "clarify_end": "clarify_end",
        "block_end": "block_end",
        "shrink_and_continue": "soil_data_query",
        "continue": "soil_data_query",
    },
    "soil_data_query": {"continue": "soil_rule_engine", "fallback": "fallback_guard"},
    "soil_rule_engine": {
        "template_only": "template_render",
        "advice_only": "advice_compose",
        "template_and_advice": "template_render",
        "response_only": "response_generate",
    },
    "template_render": {"go_advice": "advice_compose", "go_response": "response_generate"},
    "advice_compose": {"continue": "response_generate"},
    "response_generate": {"continue": "data_fact_check"},
    "data_fact_check": {
        "retry_response": "response_generate",
        "go_verify": "answer_verify",
        "fallback": "fallback_guard",
    },
    "answer_verify": {"verified_end": "verified_end", "fallback": "fallback_guard"},
    "fallback_guard": {"fallback_end": "fallback_end"},
}

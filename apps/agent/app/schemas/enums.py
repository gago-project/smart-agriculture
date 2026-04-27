"""Schema definitions for enums within the soil agent."""

from __future__ import annotations

from enum import StrEnum


class InputType(StrEnum):
    """Supported input categories recognized by the soil agent."""
    BUSINESS_DIRECT = "business_direct"
    BUSINESS_COLLOQUIAL = "business_colloquial"
    CONVERSATION_CLOSING = "conversation_closing"
    GREETING = "greeting"
    CAPABILITY_QUESTION = "capability_question"
    MEANINGLESS_INPUT = "meaningless_input"
    AMBIGUOUS_LOW_CONFIDENCE = "ambiguous_low_confidence"
    OUT_OF_DOMAIN = "out_of_domain"


class IntentType(StrEnum):
    """Supported business intents recognized by the soil agent."""
    SOIL_RECENT_SUMMARY = "soil_recent_summary"
    SOIL_SEVERITY_RANKING = "soil_severity_ranking"
    SOIL_REGION_QUERY = "soil_region_query"
    SOIL_DEVICE_QUERY = "soil_device_query"
    SOIL_DIAGNOSE = "soil_diagnose"
    CLARIFICATION_NEEDED = "clarification_needed"
    OUT_OF_SCOPE = "out_of_scope"


class AnswerType(StrEnum):
    """Five canonical answer types for the LLM + FC agent.

    guidance_answer absorbs: safe_hint, clarification, boundary, closing.
    output_mode carries the sub-type within summary/ranking/detail answers.
    """
    SUMMARY = "soil_summary_answer"
    RANKING = "soil_ranking_answer"
    DETAIL = "soil_detail_answer"
    GUIDANCE = "guidance_answer"
    FALLBACK = "fallback_answer"


class OutputMode(StrEnum):
    """Sub-type of a business answer, expressed as output presentation focus."""
    NORMAL = "normal"
    ANOMALY_FOCUS = "anomaly_focus"
    WARNING_MODE = "warning_mode"
    ADVICE_MODE = "advice_mode"


class GuidanceReason(StrEnum):
    """Why a guidance_answer was issued instead of a business answer."""
    CLARIFICATION = "clarification"
    SAFE_HINT = "safe_hint"
    BOUNDARY = "boundary"
    CLOSING = "closing"


class FallbackReason(StrEnum):
    """Why a fallback_answer was issued."""
    NO_DATA = "no_data"
    ENTITY_NOT_FOUND = "entity_not_found"
    TOOL_MISSING = "tool_missing"
    TOOL_BLOCKED = "tool_blocked"
    FACT_CHECK_FAILED = "fact_check_failed"
    UNKNOWN = "unknown"

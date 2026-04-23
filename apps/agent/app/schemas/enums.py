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
    SOIL_ANOMALY_QUERY = "soil_anomaly_query"
    SOIL_WARNING_GENERATION = "soil_warning_generation"
    SOIL_METRIC_EXPLANATION = "soil_metric_explanation"
    SOIL_MANAGEMENT_ADVICE = "soil_management_advice"
    CLARIFICATION_NEEDED = "clarification_needed"
    OUT_OF_SCOPE = "out_of_scope"


class AnswerType(StrEnum):
    """Supported answer types returned by the soil agent."""
    CLOSING = "closing_answer"
    SAFE_HINT = "safe_hint_answer"
    CLARIFICATION = "clarification_answer"
    BOUNDARY = "boundary_answer"
    FALLBACK = "fallback_answer"
    SUMMARY = "soil_summary_answer"
    RANKING = "soil_ranking_answer"
    DETAIL = "soil_detail_answer"
    ANOMALY = "soil_anomaly_answer"
    WARNING = "soil_warning_answer"
    ADVICE = "soil_advice_answer"

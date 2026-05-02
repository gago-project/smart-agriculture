"""FastAPI dependency factories for the deterministic `/chat-v2` service."""

from __future__ import annotations


from functools import lru_cache
import os

from app.llm.qwen_client import QwenClient
from app.services.data_answer_service import DataAnswerService
from app.services.llm_follow_up_resolver_service import LlmFollowUpResolverService
from app.services.llm_input_guard_service import LlmInputGuardService


@lru_cache(maxsize=1)
def get_data_answer_service() -> DataAnswerService:
    """Return the deterministic data-answer service used by `/chat-v2`."""
    guard_client = QwenClient(
        api_key=os.getenv("QWEN_API_KEY", ""),
        model="qwen-turbo",
        fallback_models=["qwen-turbo"],
        timeout_seconds=3.0,
    )
    return DataAnswerService(
        llm_input_guard=LlmInputGuardService(guard_client, timeout_seconds=3.0),
        llm_follow_up_resolver=LlmFollowUpResolverService(guard_client, timeout_seconds=3.0),
    )

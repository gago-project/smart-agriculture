"""FastAPI dependency factories for shared Agent runtime objects.

The Agent service is expensive enough to build once per process: it owns the
repository, Redis-backed context store, optional Qwen client, and all Flow
nodes.  This module centralizes that construction so API routers remain thin
transport adapters and do not know how the agent is assembled.
"""

from __future__ import annotations


from functools import lru_cache
import os

from app.db.redis import RedisRuntime
from app.llm.qwen_client import QwenClient
from app.repositories.session_context_repository import SessionContextRepository
from app.services.data_answer_service import DataAnswerService
from app.services.agent_service import SoilAgentService
from app.services.llm_input_guard_service import LlmInputGuardService


@lru_cache(maxsize=1)
def get_agent_service() -> SoilAgentService:
    """Return the singleton `SoilAgentService` used by HTTP handlers.

    Redis and Qwen are optional runtime capabilities.  If Redis is not
    configured or the dependency is unavailable, `SessionContextRepository`
    falls back to its in-memory implementation for local tests.  If Qwen has
    no key, the restricted Flow still works with deterministic rule/template
    answers instead of failing the request.
    """
    redis_client = RedisRuntime(os.getenv("REDIS_URL", "")).create_client()
    context_repository = SessionContextRepository(redis_client=redis_client) if redis_client else SessionContextRepository()
    qwen_client = QwenClient(api_key=os.getenv("QWEN_API_KEY", ""))
    return SoilAgentService(context_store=context_repository, qwen_client=qwen_client)


@lru_cache(maxsize=1)
def get_data_answer_service() -> DataAnswerService:
    """Return the deterministic data-answer service used by `/chat-v2`."""
    guard_client = QwenClient(
        api_key=os.getenv("QWEN_API_KEY", ""),
        model="qwen-turbo",
        fallback_models=["qwen-turbo"],
        timeout_seconds=3.0,
    )
    return DataAnswerService(llm_input_guard=LlmInputGuardService(guard_client, timeout_seconds=3.0))

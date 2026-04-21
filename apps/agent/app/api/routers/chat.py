from __future__ import annotations

"""HTTP routes that expose the Soil Agent chat contract.

The router deliberately performs only request/response adaptation.  All intent
recognition, slot resolution, SQL planning, rule execution, answer generation,
fact checking, verification, logging, and context persistence happen inside
`SoilAgentService`.  Database errors are not swallowed here because the product
requirement is "连接失败就报错，不允许假 fallback 数据"。
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_agent_service
from app.repositories.soil_repository import DatabaseQueryError, DatabaseUnavailableError
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse
from app.services.agent_service import SoilAgentService


router = APIRouter(prefix="", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, service: SoilAgentService = Depends(get_agent_service)) -> ChatResponse:
    """Run the primary chat endpoint used by Next BFF and direct smoke tests.

    `ChatRequest` accepts the external `message` field and normalizes it to
    `user_input`.  The response model preserves the full Flow contract so tests
    can assert node path, query plan, final status, and final answer together.
    """
    try:
        return ChatResponse(
            **await service.achat(
                request.user_input,
                session_id=request.session_id,
                turn_id=request.turn_id,
                request_id=request.request_id,
                channel=request.channel,
                timezone=request.timezone,
            )
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{exc}") from exc
    except DatabaseQueryError as exc:
        raise HTTPException(status_code=500, detail=f"数据库查询失败：{exc}") from exc


@router.post("/analyze", response_model=ChatResponse)
async def analyze(request: ChatRequest, service: SoilAgentService = Depends(get_agent_service)) -> ChatResponse:
    """Compatibility endpoint with the same behavior as `/chat`.

    Keeping `/analyze` avoids breaking older local scripts while still routing
    through the exact same service path.  This prevents "analyze" and "chat"
    from drifting into two subtly different agent implementations.
    """
    try:
        return ChatResponse(
            **await service.achat(
                request.user_input,
                session_id=request.session_id,
                turn_id=request.turn_id,
                request_id=request.request_id,
                channel=request.channel,
                timezone=request.timezone,
            )
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{exc}") from exc
    except DatabaseQueryError as exc:
        raise HTTPException(status_code=500, detail=f"数据库查询失败：{exc}") from exc

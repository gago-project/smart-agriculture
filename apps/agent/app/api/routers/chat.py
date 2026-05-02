"""HTTP route that exposes the deterministic soil-data chat contract."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_data_answer_service
from app.repositories.soil_repository import DatabaseQueryError, DatabaseUnavailableError
from app.schemas.request import ChatV2Request
from app.services.data_answer_service import DataAnswerService


router = APIRouter(prefix="", tags=["chat"])


@router.post("/chat-v2")
async def chat_v2(
    request: ChatV2Request,
    service: DataAnswerService = Depends(get_data_answer_service),
) -> dict:
    """Run the deterministic server-session chat contract used by the BFF."""
    try:
        return await service.reply(
            message=request.user_input,
            session_id=request.session_id,
            turn_id=request.turn_id,
            current_context=request.current_context,
            timezone=request.timezone,
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{exc}") from exc
    except DatabaseQueryError as exc:
        raise HTTPException(status_code=500, detail=f"数据库查询失败：{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

"""HTTP routes that expose the Soil Agent chat contract.

The router deliberately performs only request/response adaptation.  All intent
recognition, slot resolution, SQL planning, rule execution, answer generation,
fact checking, verification, logging, and context persistence happen inside
`SoilAgentService`.  Database errors are not swallowed here because the product
requirement is "连接失败就报错，不允许假 fallback 数据"。

P2-15: /chat/stream emits Server-Sent Events with stage progress markers
(stage_started, stage_completed, final_answer, error) so long agent runs can
show progressive UI without waiting for the full pipeline to finish.
"""

from __future__ import annotations


import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_agent_service, get_data_answer_service
from app.repositories.soil_repository import DatabaseQueryError, DatabaseUnavailableError
from app.schemas.request import ChatRequest, ChatV2Request
from app.schemas.response import ChatResponse
from app.services.agent_service import SoilAgentService
from app.services.data_answer_service import DataAnswerService


router = APIRouter(prefix="", tags=["chat"])


def _sse_event(event: str, data: dict) -> bytes:
    """Render a single SSE event line in `event: NAME\\ndata: JSON\\n\\n` form."""
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    ).encode("utf-8")


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


@router.post("/chat-v2")
async def chat_v2(
    request: ChatV2Request,
    service: DataAnswerService = Depends(get_data_answer_service),
) -> dict:
    """Run the deterministic server-session chat contract used by the new BFF."""
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


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    service: SoilAgentService = Depends(get_agent_service),
) -> StreamingResponse:
    """Server-Sent Events stream of chat progress.

    Emits these events:
      - `stage_started`   {"stage": "agent_loop"}      pipeline begins
      - `stage_completed` {"stage": "agent_loop", ...} after the agent run
      - `final_answer`    full ChatResponse payload
      - `error`           {"detail": "..."}            on database/LLM errors

    The current implementation runs the full pipeline once (so we still get a
    consistent answer + audit trail) and streams progress markers around it.
    A future iteration can plug into AgentLoopService for per-tool granularity.
    """

    async def event_stream():
        yield _sse_event("stage_started", {"stage": "agent_loop"})
        try:
            result = await service.achat(
                request.user_input,
                session_id=request.session_id,
                turn_id=request.turn_id,
                request_id=request.request_id,
                channel=request.channel,
                timezone=request.timezone,
            )
        except DatabaseUnavailableError as exc:
            yield _sse_event("error", {"detail": f"数据库不可用：{exc}", "code": 503})
            return
        except DatabaseQueryError as exc:
            yield _sse_event("error", {"detail": f"数据库查询失败：{exc}", "code": 500})
            return

        yield _sse_event("stage_completed", {
            "stage": "agent_loop",
            "tool_call_count": len(result.get("tool_trace") or []),
            "fallback_reason": result.get("fallback_reason"),
        })
        # Allow client buffer to flush before the final payload
        await asyncio.sleep(0)
        yield _sse_event("final_answer", result)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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

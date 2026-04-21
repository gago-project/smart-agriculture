from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_agent_service
from app.repositories.soil_repository import DatabaseQueryError, DatabaseUnavailableError
from app.services.agent_service import SoilAgentService


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/summary")
def summary(service: SoilAgentService = Depends(get_agent_service)) -> dict:
    try:
        return service.get_summary_payload()
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{exc}") from exc
    except DatabaseQueryError as exc:
        raise HTTPException(status_code=500, detail=f"数据库查询失败：{exc}") from exc


@router.get("/traces/{trace_id}")
def trace_detail(trace_id: str, service: SoilAgentService = Depends(get_agent_service)) -> dict:
    return {
        "trace_id": trace_id,
        "snapshots": service.debug_service.list_trace_snapshots(trace_id),
    }

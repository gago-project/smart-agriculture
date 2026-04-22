"""HTTP route handlers for health endpoints."""

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight health payload for liveness checks."""
    return {"status": "ok", "service": "smart-agriculture-agent"}

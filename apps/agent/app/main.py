from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.services.agent_service import SoilAgentService


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = "default"
    turn_id: int = 1


app = FastAPI(title="Smart Agriculture Soil Agent", version="0.1.0")
service = SoilAgentService()


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "smart-agriculture-agent"}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    return service.chat(request.message, session_id=request.session_id, turn_id=request.turn_id)


@app.post("/analyze")
def analyze(request: ChatRequest) -> dict[str, Any]:
    return service.chat(request.message, session_id=request.session_id, turn_id=request.turn_id)


@app.get("/summary")
def summary() -> dict[str, Any]:
    return service.get_summary_payload()

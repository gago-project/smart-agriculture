from __future__ import annotations

"""FastAPI application entrypoint for the Python Soil Moisture Agent.

This file intentionally stays small: it wires logging once, creates the
FastAPI app, and mounts the routers that expose health, chat, and debug
capabilities.  Business flow logic lives in `services/agent_service.py` and
the `flow/` package so that startup concerns do not mix with agent reasoning.
"""

from fastapi import FastAPI

from app.api.routers.chat import router as chat_router
from app.api.routers.debug import router as debug_router
from app.api.routers.health import router as health_router
from app.config.logging import configure_logging


# Configure process-level logging before FastAPI registers routes.  Keeping
# this at module load time ensures Docker/uvicorn logs have a consistent shape.
configure_logging()

# The app object is imported by uvicorn in Docker and local scripts.  Router
# registration order is simple and explicit so health checks never depend on
# heavier chat/debug modules.
app = FastAPI(title="Smart Agriculture Soil Agent", version="0.1.0")
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(debug_router)

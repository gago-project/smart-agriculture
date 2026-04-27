"""Soil Moisture Agent flow orchestrator — LLM + Function Calling edition."""
from __future__ import annotations

from app.flow.runner import FlowRunner, RouteRegistry
from app.flow.routes import ROUTES
from app.flow.nodes import (
    AgentLoopNode,
    AnswerVerifyNode,
    DataFactCheckNode,
    FallbackGuardNode,
    InputGuardNode,
)


class SoilMoistureFlowOrchestrator:
    """Thin wrapper that wires the 5-node agent flow."""

    def __init__(self, *, nodes: dict[str, object], debug_service=None):
        self.runner = FlowRunner(
            nodes=nodes,
            routes=RouteRegistry(ROUTES),
            entrypoint="input_guard",
            terminals={"safe_end", "clarify_end", "boundary_end", "closing_end",
                       "block_end", "verified_end", "fallback_end"},
            fallback_node_name="fallback_guard",
            debug_service=debug_service,
        )

    async def run(self, state):
        return await self.runner.run(state)

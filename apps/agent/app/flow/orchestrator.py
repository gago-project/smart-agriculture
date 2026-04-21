from __future__ import annotations

"""Orchestrator wrapper that binds registered nodes to the static Flow runner."""

from app.flow.runner import FlowRunner, RouteRegistry
from app.flow.routes import ROUTES
from app.flow.nodes import (
    AdviceComposeNode,
    AnswerVerifyNode,
    DataFactCheckNode,
    ExecutionGateNode,
    FallbackGuardNode,
    HistoryContextMergeNode,
    InputGuardNode,
    IntentSlotExtractNode,
    RegionResolveNode,
    ResponseGenerateNode,
    SoilDataQueryNode,
    SoilRuleEngineNode,
    TemplateRenderNode,
    TimeResolveNode,
)


class SoilMoistureFlowOrchestrator:
    """Small façade around `FlowRunner` with Soil Agent terminal states."""

    def __init__(self, *, nodes: dict[str, object], debug_service=None):
        """Create the runner using the plans-defined entrypoint and terminals."""
        self.runner = FlowRunner(
            nodes=nodes,
            routes=RouteRegistry(ROUTES),
            entrypoint="input_guard",
            terminals={"safe_end", "clarify_end", "boundary_end", "block_end", "verified_end", "fallback_end"},
            fallback_node_name="fallback_guard",
            debug_service=debug_service,
        )

    async def run(self, state):
        """Run a `FlowState` through the configured restricted Flow."""
        return await self.runner.run(state)

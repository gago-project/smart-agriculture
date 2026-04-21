from __future__ import annotations

"""Restricted Flow runner used by the Soil Moisture Agent.

This module is the execution kernel for the plans-defined agent architecture.
It does not decide business intent and it does not query data directly; it only
executes registered nodes, validates that each node returns an allowed action,
merges the node patch into `FlowState`, records trace/debug snapshots, and
applies hard safety limits around loops/retries/step count.
"""

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel

from app.repositories.soil_repository import DatabaseQueryError, DatabaseUnavailableError
from app.schemas.state import BundleModel, FlowState, NodeResult


class FlowNode(Protocol):
    """Protocol every Flow node must satisfy.

    The three declarative attributes make the Flow auditable:
    - `name` identifies the node in route tables and `node_trace`;
    - `allowed_next_actions` prevents free-form node routing;
    - `allowed_patch_fields` prevents a node from mutating unrelated state.
    """

    name: str
    allowed_next_actions: tuple[str, ...]
    allowed_patch_fields: tuple[str, ...]

    async def run(self, state: FlowState) -> NodeResult: ...


class RouteRegistry:
    """Small route-table wrapper that validates node transitions upfront."""

    def __init__(self, routes: dict[str, dict[str, str]]):
        """Store the static route table loaded from `flow/routes.py`."""
        self.routes = routes

    def resolve(self, *, node_name: str, next_action: str, state: FlowState) -> str:
        """Return the next node/terminal for a node action.

        `state` is accepted for future conditional routing, but the current
        implementation intentionally uses a fixed table so the Flow remains
        deterministic and easy to compare with the design documents.
        """
        del state
        try:
            return self.routes[node_name][next_action]
        except KeyError as exc:
            raise ValueError(f"No route for node={node_name!r} next_action={next_action!r}") from exc

    def validate(self, *, nodes: dict[str, FlowNode], terminals: set[str]) -> None:
        """Fail fast when routes and node declarations diverge.

        This is a guardrail against the class of bugs where a node returns an
        action that is not in the route table, or a route points at a node that
        was never registered in the orchestrator.
        """
        for node_name in nodes:
            if node_name not in self.routes:
                raise ValueError(f"No route table for node={node_name!r}")
            if not self.routes[node_name]:
                raise ValueError(f"No route for node={node_name!r}")
            node = nodes[node_name]
            if set(self.routes[node_name].keys()) != set(node.allowed_next_actions):
                raise ValueError(f"Route actions for node={node_name!r} do not match node declaration")
            for action, target in self.routes[node_name].items():
                if not action:
                    raise ValueError(f"Empty next_action for node={node_name!r}")
                if target not in nodes and target not in terminals:
                    raise ValueError(f"Route target {target!r} for node={node_name!r} is not registered")

def merge_state_patch(state: FlowState, patch: dict[str, Any], *, allowed_fields: tuple[str, ...] | None = None) -> FlowState:
    """Apply a node patch to `FlowState` with field-level safety checks.

    Bundle fields such as `query_plan` and `query_result` are merged rather
    than replaced so each node can add the subset it owns.  Plain lists are
    extended, which is used by logs/traces.  Unknown or forbidden fields raise
    immediately because silent state mutation would make the agent hard to
    reason about.
    """
    for key, value in patch.items():
        if not hasattr(state, key):
            raise ValueError(f"Unknown FlowState field {key!r}")
        if allowed_fields is not None and key not in allowed_fields:
            raise ValueError(f"Field {key!r} is not allowed in this node patch")
        current_value = getattr(state, key)
        if isinstance(current_value, BundleModel) and isinstance(value, (dict, BaseModel)):
            current_value.update(value)
        elif isinstance(current_value, dict) and isinstance(value, dict):
            current_value.update(value)
        elif isinstance(current_value, list) and isinstance(value, list):
            current_value.extend(value)
        else:
            setattr(state, key, value)
    return state


class FlowRunner:
    """Execute the restricted node graph until a terminal status is reached."""

    def __init__(
        self,
        *,
        nodes: dict[str, FlowNode],
        routes: RouteRegistry,
        entrypoint: str,
        terminals: set[str],
        max_steps: int = 32,
        max_retry_count: int = 2,
        max_node_visits_per_node: int = 4,
        fallback_node_name: str = "fallback_guard",
        debug_service=None,
    ):
        """Create a runner and validate that routes match registered nodes.

        `max_steps`, `max_retry_count`, and `max_node_visits_per_node` are hard
        circuit breakers.  They protect production requests from accidental
        route cycles or retry storms and force a controlled fallback instead.
        """
        if entrypoint not in nodes:
            raise ValueError(f"Entrypoint {entrypoint!r} is not registered")
        self.nodes = nodes
        self.routes = routes
        self.entrypoint = entrypoint
        self.terminals = terminals
        self.max_steps = max_steps
        self.max_retry_count = max_retry_count
        self.max_node_visits_per_node = max_node_visits_per_node
        self.fallback_node_name = fallback_node_name
        self.debug_service = debug_service
        self.routes.validate(nodes=nodes, terminals=terminals)

    async def run(self, state: FlowState) -> FlowState:
        """Run the Flow from `entrypoint` until a terminal state is produced."""
        current_node = self.entrypoint
        while current_node:
            # Count every hop before running the node so even a node that keeps
            # returning to itself is stopped deterministically.
            state.step_count += 1
            state.node_visit_counts[current_node] = state.node_visit_counts.get(current_node, 0) + 1
            if state.step_count > self.max_steps:
                state.answer_bundle["final_answer"] = "当前请求执行步骤过多，已安全降级，请缩小问题范围后重试。"
                return await self._run_fallback(state)
            if state.node_visit_counts[current_node] > self.max_node_visits_per_node:
                state.answer_bundle["final_answer"] = "当前请求循环次数过多，已安全降级，请换一种问法重试。"
                return await self._run_fallback(state)
            if state.retry_count > self.max_retry_count:
                state.answer_bundle["final_answer"] = "当前请求重试次数过多，已安全降级，请稍后再试。"
                return await self._run_fallback(state)

            node = self.nodes[current_node]
            state, result = await self._run_node_with_snapshot(node=node, state=state)

            try:
                next_target = self.routes.resolve(node_name=current_node, next_action=result.next_action, state=state)
            except ValueError:
                # Nodes may choose the generic `fallback` action in exceptional
                # business cases.  Unknown non-fallback actions still surface as
                # configuration bugs so tests catch route drift.
                if result.next_action == "fallback":
                    return await self._run_fallback(state)
                raise
            if next_target in self.terminals:
                state.final_status = next_target
                return state
            current_node = next_target

        state.answer_bundle["final_answer"] = "当前请求未能完成，已安全降级。"
        return await self._run_fallback(state)

    async def _run_fallback(self, state: FlowState) -> FlowState:
        """Execute the fallback node exactly once and mark `fallback_end`."""
        if self.fallback_node_name not in self.nodes:
            state.final_status = "fallback_end"
            return state
        fallback_node = self.nodes[self.fallback_node_name]
        state, result = await self._run_node_with_snapshot(node=fallback_node, state=state)
        state.final_status = "fallback_end"
        return state

    async def _run_node_with_snapshot(self, *, node: FlowNode, state: FlowState) -> tuple[FlowState, NodeResult]:
        """Run one node, merge its patch, and optionally persist debug output."""
        node_name = node.name
        started_at = datetime.now()
        state.node_trace.append(f"{node_name}:start")
        try:
            result = await node.run(state)
            state = merge_state_patch(state, result.state_patch, allowed_fields=node.allowed_patch_fields)
            state.node_trace.append(f"{node_name}:{result.next_action}")
            if self.debug_service:
                # Snapshots are intentionally summarized rather than storing
                # full state because query results can be large and may contain
                # operational details that should not flood debug storage.
                await self.debug_service.save_node_snapshot(
                    trace_id=state.trace_id,
                    request_id=state.request_id,
                    session_id=state.session_id,
                    turn_id=state.turn_id,
                    node_name=node_name,
                    status=result.node_status,
                    started_at=started_at,
                    finished_at=datetime.now(),
                    input_summary=self.debug_service.summarize_state_for_node_input(state, node_name),
                    output_summary=self.debug_service.summarize_state_for_node_output(state, node_name),
            )
            return state, result
        except (DatabaseUnavailableError, DatabaseQueryError):
            # Database failures are re-raised so the API layer can return a
            # real 5xx error instead of fabricating an answer.
            raise
        except Exception as exc:
            # Non-database node failures are converted into safe fallback.  The
            # original error is still captured in state/debug snapshots for
            # diagnosis.
            state.errors.append({"code": "NODE_EXECUTION_FAILED", "message": f"{node_name} failed: {exc}"})
            if self.debug_service:
                await self.debug_service.save_node_snapshot(
                    trace_id=state.trace_id,
                    request_id=state.request_id,
                    session_id=state.session_id,
                    turn_id=state.turn_id,
                    node_name=node_name,
                    status="failed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    input_summary=self.debug_service.summarize_state_for_node_input(state, node_name),
                    output_summary={},
                    error_code="NODE_EXECUTION_FAILED",
                    error_message=str(exc),
                )
            return state, NodeResult(next_action="fallback", node_status="failed")

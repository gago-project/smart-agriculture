from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any, Protocol

from app.schemas.state import FlowState, NodeResult


class FlowNode(Protocol):
    async def run(self, state: FlowState) -> NodeResult: ...


class RouteRegistry:
    def __init__(self, routes: dict[str, dict[str, str]]):
        self.routes = routes

    def resolve(self, *, node_name: str, next_action: str, state: FlowState) -> str:
        try:
            return self.routes[node_name][next_action]
        except KeyError as exc:
            raise ValueError(f"No route for node={node_name!r} next_action={next_action!r}") from exc

    def validate(self, *, nodes: dict[str, FlowNode], terminals: set[str]) -> None:
        for node_name in nodes:
            if node_name not in self.routes:
                raise ValueError(f"No route table for node={node_name!r}")
            if not self.routes[node_name]:
                raise ValueError(f"No route for node={node_name!r}")
            for action, target in self.routes[node_name].items():
                if not action:
                    raise ValueError(f"Empty next_action for node={node_name!r}")
                if target not in nodes and target not in terminals:
                    raise ValueError(f"Route target {target!r} for node={node_name!r} is not registered")


def merge_state_patch(state: FlowState, patch: dict[str, Any]) -> FlowState:
    for key, value in patch.items():
        if not hasattr(state, key):
            raise ValueError(f"Unknown FlowState field {key!r}")
        current_value = getattr(state, key)
        if isinstance(current_value, dict) and isinstance(value, dict):
            current_value.update(value)
        else:
            setattr(state, key, value)
    return state


class FlowRunner:
    def __init__(
        self,
        *,
        nodes: dict[str, FlowNode],
        routes: RouteRegistry,
        entrypoint: str,
        terminals: set[str],
        max_steps: int = 32,
        max_retry_count: int = 2,
    ):
        if entrypoint not in nodes:
            raise ValueError(f"Entrypoint {entrypoint!r} is not registered")
        self.nodes = nodes
        self.routes = routes
        self.entrypoint = entrypoint
        self.terminals = terminals
        self.max_steps = max_steps
        self.max_retry_count = max_retry_count
        self.routes.validate(nodes=nodes, terminals=terminals)

    async def run(self, state: FlowState) -> FlowState:
        current_node = self.entrypoint
        while current_node:
            state.step_count += 1
            state.node_visit_counts[current_node] = state.node_visit_counts.get(current_node, 0) + 1
            if state.step_count > self.max_steps:
                state.final_status = "fallback_end"
                state.answer_bundle["final_answer"] = "当前请求执行步骤过多，已安全降级，请缩小问题范围后重试。"
                return state

            node = self.nodes[current_node]
            state.node_trace.append(f"{current_node}:start")
            result = await node.run(state)
            state = merge_state_patch(state, result.state_patch)
            state.node_trace.append(f"{current_node}:{result.next_action}")

            next_target = self.routes.resolve(node_name=current_node, next_action=result.next_action, state=state)
            if next_target in self.terminals:
                state.final_status = next_target
                return state
            current_node = next_target

        state.final_status = "fallback_end"
        state.answer_bundle["final_answer"] = "当前请求未能完成，已安全降级。"
        return state

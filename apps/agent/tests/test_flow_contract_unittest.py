import asyncio
import unittest

from app.flow.runner import FlowRunner, RouteRegistry
from app.schemas.state import FlowState, NodeResult


class StaticNode:
    def __init__(self, action, patch=None):
        self.action = action
        self.patch = patch or {}

    async def run(self, state):
        return NodeResult(next_action=self.action, state_patch=self.patch)


class FlowContractTest(unittest.TestCase):
    def test_route_registry_rejects_missing_next_action(self):
        nodes = {"input_guard": StaticNode("continue")}
        routes = RouteRegistry({"input_guard": {}})

        with self.assertRaisesRegex(ValueError, "No route"):
            routes.validate(nodes=nodes, terminals={"verified_end"})

    def test_fallback_flows_through_fallback_guard(self):
        async def run_case():
            nodes = {
                "input_guard": StaticNode("fallback", {"answer_bundle": {"final_answer": "bad draft"}}),
                "fallback_guard": StaticNode("fallback_end", {"answer_bundle": {"final_answer": "safe fallback"}}),
            }
            routes = RouteRegistry({
                "input_guard": {"fallback": "fallback_guard"},
                "fallback_guard": {"fallback_end": "fallback_end"},
            })
            runner = FlowRunner(nodes=nodes, routes=routes, entrypoint="input_guard", terminals={"fallback_end"})
            return await runner.run(FlowState(request_id="r1", session_id="s1", turn_id=1, user_input="x"))

        final_state = asyncio.run(run_case())

        self.assertEqual(final_state.final_status, "fallback_end")
        self.assertEqual(final_state.answer_bundle["final_answer"], "safe fallback")
        self.assertEqual(final_state.node_trace, [
            "input_guard:start",
            "input_guard:fallback",
            "fallback_guard:start",
            "fallback_guard:fallback_end",
        ])

    def test_runner_stops_when_max_steps_exceeded(self):
        async def run_case():
            nodes = {"input_guard": StaticNode("continue")}
            routes = RouteRegistry({"input_guard": {"continue": "input_guard"}})
            runner = FlowRunner(nodes=nodes, routes=routes, entrypoint="input_guard", terminals={"fallback_end"}, max_steps=2)
            return await runner.run(FlowState(request_id="r1", session_id="s1", turn_id=1, user_input="x"))

        final_state = asyncio.run(run_case())

        self.assertEqual(final_state.final_status, "fallback_end")
        self.assertIn("步骤过多", final_state.answer_bundle["final_answer"])


if __name__ == "__main__":
    unittest.main()

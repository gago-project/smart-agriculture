import asyncio
import unittest

from app.flow.routes import ROUTES
from app.flow.runner import FlowRunner, RouteRegistry
from app.repositories.soil_repository import DatabaseUnavailableError
from app.schemas.state import FlowState, NodeResult


class StaticNode:
    allowed_patch_fields = ("answer_bundle",)

    def __init__(self, action, patch=None, *, name="static", allowed_next_actions=None):
        self.action = action
        self.patch = patch or {}
        self.name = name
        self.allowed_next_actions = allowed_next_actions or (action,)

    async def run(self, state):
        return NodeResult(next_action=self.action, state_patch=self.patch)


class DatabaseFailingNode:
    name = "input_guard"
    allowed_next_actions = ("continue",)
    allowed_patch_fields = ()

    async def run(self, state):
        del state
        raise DatabaseUnavailableError("mysql down")


class FlowContractTest(unittest.TestCase):
    def test_route_table_matches_latest_plan_actions(self):
        self.assertEqual(
            ROUTES["execution_gate"],
            {
                "clarify_end": "clarify_end",
                "block_end": "block_end",
                "shrink_and_continue": "soil_data_query",
                "continue": "soil_data_query",
            },
        )
        self.assertEqual(
            ROUTES["soil_rule_engine"],
            {
                "template_only": "template_render",
                "advice_only": "advice_compose",
                "template_and_advice": "template_render",
                "response_only": "response_generate",
            },
        )
        self.assertEqual(
            ROUTES["template_render"],
            {
                "go_advice": "advice_compose",
                "go_response": "response_generate",
            },
        )

    def test_route_registry_rejects_missing_next_action(self):
        nodes = {"input_guard": StaticNode("continue")}
        routes = RouteRegistry({"input_guard": {}})

        with self.assertRaisesRegex(ValueError, "No route"):
            routes.validate(nodes=nodes, terminals={"verified_end"})

    def test_fallback_flows_through_fallback_guard(self):
        async def run_case():
            nodes = {
                "input_guard": StaticNode("fallback", {"answer_bundle": {"final_answer": "bad draft"}}, name="input_guard"),
                "fallback_guard": StaticNode("fallback_end", {"answer_bundle": {"final_answer": "safe fallback"}}, name="fallback_guard"),
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

    def test_database_unavailable_error_is_not_converted_to_fallback(self):
        async def run_case():
            nodes = {
                "input_guard": DatabaseFailingNode(),
                "fallback_guard": StaticNode("fallback_end", {"answer_bundle": {"final_answer": "safe fallback"}}, name="fallback_guard"),
            }
            routes = RouteRegistry({
                "input_guard": {"continue": "fallback_guard"},
                "fallback_guard": {"fallback_end": "fallback_end"},
            })
            runner = FlowRunner(nodes=nodes, routes=routes, entrypoint="input_guard", terminals={"fallback_end"})
            await runner.run(FlowState(request_id="r1", session_id="s1", turn_id=1, user_input="x"))

        with self.assertRaises(DatabaseUnavailableError):
            asyncio.run(run_case())

    def test_runner_stops_when_max_steps_exceeded(self):
        async def run_case():
            nodes = {"input_guard": StaticNode("continue", name="input_guard")}
            routes = RouteRegistry({"input_guard": {"continue": "input_guard"}})
            nodes["fallback_guard"] = StaticNode("fallback_end", {"answer_bundle": {"final_answer": "safe fallback"}}, name="fallback_guard")
            routes = RouteRegistry({
                "input_guard": {"continue": "input_guard"},
                "fallback_guard": {"fallback_end": "fallback_end"},
            })
            runner = FlowRunner(nodes=nodes, routes=routes, entrypoint="input_guard", terminals={"fallback_end"}, max_steps=2)
            return await runner.run(FlowState(request_id="r1", session_id="s1", turn_id=1, user_input="x"))

        final_state = asyncio.run(run_case())

        self.assertEqual(final_state.final_status, "fallback_end")
        self.assertEqual(final_state.answer_bundle["final_answer"], "safe fallback")

    def test_route_registry_rejects_node_action_mismatch(self):
        node = StaticNode("continue", name="input_guard", allowed_next_actions=("continue", "fallback"))
        with self.assertRaisesRegex(ValueError, "do not match"):
            RouteRegistry({"input_guard": {"continue": "fallback_end"}}).validate(nodes={"input_guard": node}, terminals={"fallback_end"})


if __name__ == "__main__":
    unittest.main()

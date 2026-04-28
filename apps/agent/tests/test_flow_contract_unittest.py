"""Unit tests for flow contract."""

import asyncio
import unittest

from app.flow.routes import ROUTES
from app.flow.nodes.fallback_guard import FallbackGuardNode
from app.flow.runner import FlowRunner, RouteRegistry
from app.repositories.soil_repository import DatabaseUnavailableError
from app.schemas.state import FlowState, NodeResult


class StaticNode:
    """Flow node for the static stage."""
    def __init__(self, action, patch=None, *, name="static", allowed_next_actions=None, allowed_patch_fields=None):
        """Initialize the static node."""
        self.action = action
        self.patch = patch or {}
        self.name = name
        self.allowed_next_actions = allowed_next_actions or (action,)
        self.allowed_patch_fields = allowed_patch_fields or ("answer_bundle",)

    async def run(self, state):
        """Execute the node and return the next flow action."""
        return NodeResult(next_action=self.action, state_patch=self.patch)


class DatabaseFailingNode:
    """Flow node for the database failing stage."""
    name = "input_guard"
    allowed_next_actions = ("continue",)
    allowed_patch_fields = ()

    async def run(self, state):
        """Execute the node and return the next flow action."""
        del state
        raise DatabaseUnavailableError("mysql down")


class ExplodingNode:
    """Flow node for the exploding stage."""
    name = "response_generate"
    allowed_next_actions = ("fallback",)
    allowed_patch_fields = ()

    async def run(self, state):
        """Execute the node and return the next flow action."""
        del state
        raise RuntimeError("boom")


class FlowContractTest(unittest.TestCase):
    """Test cases for flow contract."""
    def test_route_table_matches_5_node_architecture(self):
        """Verify route table matches the new 5-node LLM + FC architecture."""
        self.assertIn("input_guard", ROUTES)
        self.assertIn("agent_loop", ROUTES)
        self.assertIn("data_fact_check", ROUTES)
        self.assertIn("answer_verify", ROUTES)
        self.assertIn("fallback_guard", ROUTES)
        # Old pipeline nodes must NOT be in routes
        self.assertNotIn("intent_slot_extract", ROUTES)
        self.assertNotIn("conversation_boundary", ROUTES)
        self.assertNotIn("execution_gate", ROUTES)
        self.assertNotIn("soil_data_query", ROUTES)
        # New AgentLoop route
        self.assertEqual(
            ROUTES["agent_loop"],
            {"continue": "data_fact_check", "clarify": "clarify_end", "fallback": "fallback_guard"},
        )

    def test_route_registry_rejects_missing_next_action(self):
        """Verify route registry rejects missing next action."""
        nodes = {"input_guard": StaticNode("continue")}
        routes = RouteRegistry({"input_guard": {}})

        with self.assertRaisesRegex(ValueError, "No route"):
            routes.validate(nodes=nodes, terminals={"verified_end"})

    def test_fallback_flows_through_fallback_guard(self):
        """Verify fallback flows through fallback guard."""
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
        """Verify database unavailable error is not converted to fallback."""
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
        """Verify runner stops when max steps exceeded."""
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

    def test_failed_node_after_query_uses_data_backed_fallback(self):
        """Verify failed node after query uses data backed fallback."""
        async def run_case():
            nodes = {
                "input_guard": StaticNode(
                    "continue",
                    {
                        "answer_type": "soil_detail_answer",
                        "query_result": {
                            "records": [
                                {
                                    "sn": "SNS00204333",
                                    "create_time": "2026-04-21 10:00:00",
                                    "city": "南京市",
                                    "county": "江宁区",
                                    "water20cm": 42,
                                    "display_label": "重旱",
                                }
                            ]
                        },
                    },
                    name="input_guard",
                    allowed_patch_fields=("answer_type", "query_result"),
                ),
                "response_generate": ExplodingNode(),
                "fallback_guard": FallbackGuardNode(),
            }
            routes = RouteRegistry(
                {
                    "input_guard": {"continue": "response_generate"},
                    "response_generate": {"fallback": "fallback_guard"},
                    "fallback_guard": {"fallback_end": "fallback_end"},
                }
            )
            runner = FlowRunner(nodes=nodes, routes=routes, entrypoint="input_guard", terminals={"fallback_end"})
            return await runner.run(FlowState(request_id="r1", session_id="s1", turn_id=1, user_input="x"))

        final_state = asyncio.run(run_case())

        self.assertEqual(final_state.final_status, "fallback_end")
        self.assertIn("SNS00204333", final_state.answer_bundle["final_answer"])
        self.assertNotIn("当前请求处理过程中出现异常", final_state.answer_bundle["final_answer"])

    def test_route_registry_rejects_node_action_mismatch(self):
        """Verify route registry rejects node action mismatch."""
        node = StaticNode("continue", name="input_guard", allowed_next_actions=("continue", "fallback"))
        with self.assertRaisesRegex(ValueError, "do not match"):
            RouteRegistry({"input_guard": {"continue": "fallback_end"}}).validate(nodes={"input_guard": node}, terminals={"fallback_end"})


from app.flow.nodes.agent_loop import AgentLoopNode


class AgentLoopNodeContractTest(unittest.TestCase):
    def _make_node(self):
        from tests.support_repositories import SeedSoilRepository
        from app.llm.qwen_client import QwenClient
        from app.repositories.session_context_repository import SessionContextRepository
        from app.services.tool_executor_service import ToolExecutorService
        from app.services.agent_loop_service import AgentLoopService
        repo = SeedSoilRepository()
        svc = AgentLoopService(
            qwen_client=QwenClient(api_key=""),
            tool_executor=ToolExecutorService(repository=repo),
            history_store=SessionContextRepository(),
        )
        return AgentLoopNode(svc, repository=repo)

    def test_agent_loop_node_name(self):
        node = self._make_node()
        self.assertEqual(node.name, "agent_loop")

    def test_agent_loop_node_allowed_actions(self):
        node = self._make_node()
        self.assertIn("continue", node.allowed_next_actions)
        self.assertIn("fallback", node.allowed_next_actions)


if __name__ == "__main__":
    unittest.main()

import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.llm.tools import SOIL_TOOLS
from app.llm.qwen_client import QwenClient

class ToolSchemaTest(unittest.TestCase):
    def test_tool_count(self):
        # diagnose_empty_result removed; query_soil_comparison added (P2-14) — now 4 tools
        self.assertEqual(len(SOIL_TOOLS), 4)

    def test_each_tool_has_required_keys(self):
        for tool in SOIL_TOOLS:
            with self.subTest(tool=tool):
                self.assertEqual(tool["type"], "function")
                fn = tool["function"]
                self.assertIn("name", fn)
                self.assertIn("description", fn)
                params = fn["parameters"]
                self.assertEqual(params["type"], "object")
                self.assertIn("properties", params)
                self.assertIn("required", params)

    def test_each_tool_has_meta(self):
        # P2-17: every tool carries internal metadata for intent/answer_type wiring
        for tool in SOIL_TOOLS:
            with self.subTest(tool=tool["function"]["name"]):
                meta = tool.get("meta")
                self.assertIsNotNone(meta)
                self.assertIn("intent", meta)
                self.assertIn("answer_type", meta)

    def test_tool_names_match_contract(self):
        names = {t["function"]["name"] for t in SOIL_TOOLS}
        expected = {
            "query_soil_summary",
            "query_soil_ranking",
            "query_soil_detail",
            "query_soil_comparison",
        }
        self.assertEqual(names, expected)

    def test_all_tools_require_absolute_time_window(self):
        for tool in SOIL_TOOLS:
            required = tool["function"]["parameters"]["required"]
            with self.subTest(tool=tool["function"]["name"]):
                self.assertIn("start_time", required)
                self.assertIn("end_time", required)
                self.assertNotIn("time_expression", required)


class QwenClientFunctionCallingTest(unittest.TestCase):
    def setUp(self):
        self.client = QwenClient(api_key="test-key")

    def test_call_with_tools_returns_none_when_no_key(self):
        client = QwenClient(api_key="")
        result = asyncio.run(client.call_with_tools(messages=[], tools=SOIL_TOOLS))
        self.assertIsNone(result)

    def test_call_with_tools_parses_tool_call_response(self):
        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "query_soil_summary",
                            "arguments": '{"start_time": "2025-04-14 00:00:00", "end_time": "2025-04-20 23:59:59"}'
                        }
                    }]
                }
            }]
        }
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = asyncio.run(self.client.call_with_tools(
                messages=[{"role": "user", "content": "全省概况"}],
                tools=SOIL_TOOLS,
            ))
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "tool_calls")
        self.assertIsInstance(result["calls"], list)
        self.assertEqual(len(result["calls"]), 1)
        first_call = result["calls"][0]
        self.assertEqual(first_call["tool_name"], "query_soil_summary")
        self.assertIn("start_time", first_call["tool_args"])

    def test_call_with_tools_parses_text_response(self):
        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "延安市最近7天整体墒情偏干。",
                    "tool_calls": None,
                }
            }]
        }
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = asyncio.run(self.client.call_with_tools(
                messages=[{"role": "user", "content": "概况"}],
                tools=SOIL_TOOLS,
            ))
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "text")
        self.assertIn("延安", result["content"])

    def test_call_with_tools_disables_env_proxy_lookup(self):
        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "ok",
                    "tool_calls": None,
                }
            }]
        }
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

            asyncio.run(self.client.call_with_tools(
                messages=[{"role": "user", "content": "概况"}],
                tools=SOIL_TOOLS,
            ))

        self.assertEqual(mock_http.call_args.kwargs.get("trust_env"), False)

    def test_request_json_disables_env_proxy_lookup(self):
        mock_response = {
            "choices": [{
                "message": {
                    "content": "{\"resolved_input\": \"南京最近13天墒情怎么样\"}"
                }
            }]
        }
        with patch("httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

            asyncio.run(self.client._request_json(
                messages=[{"role": "user", "content": "南京最近13天墒情怎么样"}],
            ))

        self.assertEqual(mock_http.call_args.kwargs.get("trust_env"), False)


from app.llm.prompts.system_prompt import build_system_prompt


class SystemPromptTest(unittest.TestCase):
    def test_includes_latest_business_time(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        self.assertIn("2025-04-20 08:00:00", prompt)

    def test_includes_safety_constraints(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        self.assertIn("不允许", prompt)
        self.assertIn("facts", prompt.lower())

    def test_includes_absolute_time_window_instructions(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        self.assertIn("start_time", prompt)
        self.assertIn("end_time", prompt)
        self.assertIn("YYYY-MM-DD HH:MM:SS", prompt)
        self.assertNotIn("time_expression", prompt)

    def test_returns_nonempty_string(self):
        prompt = build_system_prompt(latest_business_time=None)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)

    def test_lists_all_canonical_tools(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        for tool in (
            "query_soil_summary",
            "query_soil_ranking",
            "query_soil_detail",
            "query_soil_comparison",
        ):
            self.assertIn(tool, prompt)
        # diagnose_empty_result is internal — must not be exposed to LLM
        self.assertNotIn("diagnose_empty_result", prompt)

    def test_includes_p0_rule(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        # System prompt must mention the P0 mandatory tool-call constraint
        self.assertIn("P0", prompt)

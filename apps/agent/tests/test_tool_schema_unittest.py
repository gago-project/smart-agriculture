import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.llm.tools import SOIL_TOOLS
from app.llm.qwen_client import QwenClient

class ToolSchemaTest(unittest.TestCase):
    def test_tool_count(self):
        self.assertEqual(len(SOIL_TOOLS), 7)

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

    def test_tool_names_match_contract(self):
        names = {t["function"]["name"] for t in SOIL_TOOLS}
        expected = {
            "get_soil_overview",
            "get_soil_ranking",
            "get_soil_detail",
            "get_soil_anomaly",
            "get_warning_data",
            "get_advice_context",
            "diagnose_empty_result",
        }
        self.assertEqual(names, expected)

    def test_all_tools_require_time_params(self):
        for tool in SOIL_TOOLS:
            required = tool["function"]["parameters"]["required"]
            with self.subTest(tool=tool["function"]["name"]):
                self.assertIn("start_time", required)
                self.assertIn("end_time", required)


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
                            "name": "get_soil_overview",
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
        self.assertEqual(result["type"], "tool_call")
        self.assertEqual(result["tool_name"], "get_soil_overview")
        self.assertIn("start_time", result["tool_args"])

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


from app.llm.prompts.system_prompt import build_system_prompt


class SystemPromptTest(unittest.TestCase):
    def test_includes_latest_business_time(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        self.assertIn("2025-04-20 08:00:00", prompt)

    def test_includes_safety_constraints(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        self.assertIn("不允许", prompt)
        self.assertIn("facts", prompt.lower())

    def test_includes_time_calculation_instructions(self):
        prompt = build_system_prompt(latest_business_time="2025-04-20 08:00:00")
        self.assertIn("start_time", prompt)
        self.assertIn("end_time", prompt)

    def test_returns_nonempty_string(self):
        prompt = build_system_prompt(latest_business_time=None)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)

import unittest
from app.llm.tools import SOIL_TOOLS

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

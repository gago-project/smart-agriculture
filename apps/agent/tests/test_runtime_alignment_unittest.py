"""Unit tests for runtime alignment."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.llm.qwen_client import QwenClient


class RuntimeAlignmentTest(unittest.TestCase):
    """Test cases for runtime alignment."""
    def test_requirements_include_plan_runtime_stack(self) -> None:
        requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
        content = requirements.read_text(encoding="utf-8")

        self.assertIn("pydantic-settings", content)
        self.assertIn("sqlalchemy", content.lower())
        self.assertIn("asyncmy", content.lower())
        self.assertIn("greenlet", content.lower())
        self.assertIn("httpx", content.lower())
        self.assertIn("structlog", content.lower())

    def test_agent_dockerfile_installs_build_toolchain_for_asyncmy(self) -> None:
        dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
        content = dockerfile.read_text(encoding="utf-8").lower()

        self.assertIn("build-essential", content)
        self.assertLess(content.index("build-essential"), content.index("pip install"))

    def test_db_runtime_modules_exist(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.assertTrue((project_root / "app/db/mysql.py").exists())
        self.assertTrue((project_root / "app/db/redis.py").exists())

    def test_qwen_client_exposes_call_with_tools(self) -> None:
        """Verify qwen client exposes the function calling interface."""
        client = QwenClient(api_key="")
        self.assertTrue(hasattr(client, "call_with_tools"))
        self.assertTrue(hasattr(client, "available"))

    def test_old_services_are_deleted(self) -> None:
        """Verify old pipeline service files have been removed."""
        project_root = Path(__file__).resolve().parents[1]
        for path in [
            "app/services/intent_slot_service.py",
            "app/services/response_service.py",
            "app/services/template_service.py",
            "app/services/time_service.py",
            "app/services/execution_gate_service.py",
            "app/services/soil_query_service.py",
            "app/services/rule_engine_service.py",
            "app/services/advice_service.py",
            "app/services/context_service.py",
            "app/services/conversation_boundary_service.py",
        ]:
            self.assertFalse(
                (project_root / path).exists(),
                f"Old service should be deleted: {path}",
            )

    def test_data_answer_service_uses_shared_paginated_table_helper(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        content = (project_root / "app/services/data_answer_service.py").read_text(encoding="utf-8")

        self.assertIn("def _build_paginated_table_block(", content)
        self.assertGreaterEqual(content.count("self._build_paginated_table_block("), 4)


if __name__ == "__main__":
    unittest.main()

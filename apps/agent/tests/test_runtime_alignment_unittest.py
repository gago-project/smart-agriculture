from __future__ import annotations

import inspect
import unittest
from pathlib import Path

from app.llm.qwen_client import QwenClient
from app.services import debug_service, template_service


class RuntimeAlignmentTest(unittest.TestCase):
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

    def test_debug_service_supports_node_snapshot_contract(self) -> None:
        service = debug_service.DebugService()
        self.assertTrue(hasattr(service, "save_node_snapshot"))
        self.assertTrue(hasattr(service, "list_trace_snapshots"))

    def test_qwen_client_exposes_structured_and_generation_methods(self) -> None:
        client = QwenClient(api_key="")
        self.assertTrue(hasattr(client, "extract_intent_slots"))
        self.assertTrue(hasattr(client, "generate_controlled_answer"))

    def test_template_service_uses_jinja2_runtime(self) -> None:
        source = inspect.getsource(template_service.TemplateService)
        self.assertIn("jinja2", source.lower())


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class RequirementsTest(unittest.TestCase):
    def test_requirements_include_runtime_settings_dependency(self):
        requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
        content = requirements.read_text(encoding="utf-8")

        self.assertIn("pydantic-settings", content)


if __name__ == "__main__":
    unittest.main()

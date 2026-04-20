import unittest

from app.services.agent_service import SoilAgentService


class AgentServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = SoilAgentService(repository=None)

    def test_meaningless_input_returns_safe_hint_without_query(self):
        result = self.service.chat("h d k j h sa d k l j", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "safe_hint_answer")
        self.assertFalse(result["should_query"])
        self.assertIn("墒情", result["final_answer"])

    def test_summary_question_returns_soil_summary(self):
        result = self.service.chat("最近墒情怎么样", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_summary_answer")
        self.assertEqual(result["intent"], "soil_recent_summary")
        self.assertIn("整体", result["final_answer"])

    def test_warning_question_uses_template_answer(self):
        result = self.service.chat("SNS00204333 需要发预警吗", session_id="s1", turn_id=1)

        self.assertEqual(result["answer_type"], "soil_warning_answer")
        self.assertEqual(result["intent"], "soil_warning_generation")
        self.assertIn("预警", result["final_answer"])


if __name__ == "__main__":
    unittest.main()

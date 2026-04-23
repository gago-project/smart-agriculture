"""Unit tests for input guard service."""

from __future__ import annotations

import unittest

from app.services.input_guard_service import InputGuardService


class InputGuardServiceTest(unittest.TestCase):
    """Test cases for input guard service."""

    def setUp(self) -> None:
        self.service = InputGuardService()

    def test_pure_closing_should_end_conversation(self) -> None:
        result = self.service.classify("谢谢")

        self.assertFalse(result.allow_business_flow)
        self.assertEqual(result.input_type, "conversation_closing")
        self.assertEqual(result.terminal_action, "closing_end")
        self.assertEqual(result.suggested_answer_type, "closing_answer")

    def test_thanks_with_business_signal_should_continue(self) -> None:
        result = self.service.classify("谢谢，南京呢？")

        self.assertTrue(result.allow_business_flow)
        self.assertEqual(result.terminal_action, "continue")

    def test_context_dependent_short_follow_up_should_continue(self) -> None:
        result = self.service.classify("那个情况呢")

        self.assertTrue(result.allow_business_flow)
        self.assertEqual(result.terminal_action, "continue")

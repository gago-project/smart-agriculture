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
        self.assertEqual(result.suggested_answer_type, "guidance_answer")
        self.assertEqual(result.guidance_reason, "closing")

    def test_out_of_scope_returns_boundary_guidance_reason(self) -> None:
        result = self.service.classify("查一下明天天气")

        self.assertFalse(result.allow_business_flow)
        self.assertEqual(result.suggested_answer_type, "guidance_answer")
        self.assertEqual(result.guidance_reason, "boundary")

    def test_greeting_returns_safe_hint_guidance_reason(self) -> None:
        result = self.service.classify("你好")

        self.assertFalse(result.allow_business_flow)
        self.assertEqual(result.suggested_answer_type, "guidance_answer")
        self.assertEqual(result.guidance_reason, "safe_hint")

    def test_ambiguous_low_confidence_returns_clarification_guidance_reason(self) -> None:
        result = self.service.classify("看看")

        self.assertFalse(result.allow_business_flow)
        self.assertEqual(result.suggested_answer_type, "guidance_answer")
        self.assertEqual(result.guidance_reason, "clarification")

    def test_thanks_with_business_signal_should_continue(self) -> None:
        result = self.service.classify("谢谢，南京呢？")

        self.assertTrue(result.allow_business_flow)
        self.assertEqual(result.terminal_action, "continue")

    def test_context_dependent_short_follow_up_should_continue(self) -> None:
        result = self.service.classify("那个情况呢")

        self.assertTrue(result.allow_business_flow)
        self.assertEqual(result.terminal_action, "continue")

    def test_non_business_suggested_answer_type_is_always_guidance_answer(self) -> None:
        """Every non-business path must return guidance_answer, never old type names."""
        non_business_inputs = ["谢谢", "你好", "查一下明天天气", "看看", "hello"]
        for text in non_business_inputs:
            result = self.service.classify(text)
            if not result.allow_business_flow:
                self.assertEqual(
                    result.suggested_answer_type, "guidance_answer",
                    f"Expected guidance_answer for {text!r}, got {result.suggested_answer_type!r}"
                )
                # Old type names must not appear
                self.assertNotIn(result.suggested_answer_type,
                                 ("closing_answer", "safe_hint_answer", "boundary_answer", "clarification_answer"))

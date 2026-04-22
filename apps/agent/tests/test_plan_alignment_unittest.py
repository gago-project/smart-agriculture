"""Unit tests for plan alignment."""

from __future__ import annotations

import inspect
import unittest

from pydantic import BaseModel

from app.schemas import state as state_module
from app.schemas.state import FlowState
from app.services import (
    advice_service,
    answer_verify_service,
    context_service,
    execution_gate_service,
    fact_check_service,
    input_guard_service,
    intent_slot_service,
    region_service,
    response_service,
    rule_engine_service,
    soil_query_service,
    template_service,
    time_service,
)


SERVICE_MODULES = [
    advice_service,
    answer_verify_service,
    context_service,
    execution_gate_service,
    fact_check_service,
    input_guard_service,
    intent_slot_service,
    region_service,
    response_service,
    rule_engine_service,
    soil_query_service,
    template_service,
    time_service,
]


class PlanAlignmentTest(unittest.TestCase):
    """Test cases for plan alignment."""
    def test_flow_state_is_pydantic_model_with_plan_fields(self) -> None:
        """Verify flow state is pydantic model with plan fields."""
        self.assertTrue(issubclass(FlowState, BaseModel))
        state = FlowState(
            request_id="r1",
            trace_id="t1",
            session_id="s1",
            turn_id=1,
            user_input="最近墒情怎么样",
        )
        dumped = state.model_dump()
        self.assertIn("query_log_entries", dumped)
        self.assertIn("context_to_save", dumped)
        self.assertIn("raw_slots", dumped)
        self.assertIn("business_time", dumped)

    def test_service_modules_have_real_implementations(self) -> None:
        """Verify service modules have real implementations."""
        for module in SERVICE_MODULES:
            source = inspect.getsource(module)
            self.assertNotIn("from app.services.flow_support import", source, module.__name__)

    def test_flow_support_no_longer_exports_services(self) -> None:
        """Verify flow support no longer exports services."""
        source = inspect.getsource(state_module)
        self.assertNotIn("@dataclass", source)


if __name__ == "__main__":
    unittest.main()

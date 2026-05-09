from __future__ import annotations

from types import SimpleNamespace
import unittest


class TurnInterpretationServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from app.services.turn_interpretation_service import TurnInterpretationService

        self.service = TurnInterpretationService()

    @staticmethod
    def _time_evidence(*, has_time_signal: bool, start_time: str | None = None, end_time: str | None = None):
        return SimpleNamespace(
            has_time_signal=has_time_signal,
            start_time=start_time,
            end_time=end_time,
        )

    @staticmethod
    def _base_data_context(*, closed: bool = False, capability: str = "summary", grain: str = "aggregate") -> dict:
        return {
            "topic_family": "data",
            "closed": closed,
            "query_state": {
                "capability": capability,
                "grain": grain,
                "slots": {"province": "江苏省", "city": None, "county": None, "sn": None},
                "slot_confidence": {"province": "high", "time": "high"},
                "slot_source": {"province": "explicit", "time": "explicit"},
                "time_window": {"start_time": "2026-03-15 00:00:00", "end_time": "2026-04-13 23:59:59"},
                "last_active_turn_id": 1,
            },
            "follow_up_targets": [
                {
                    "target_key": "target_1",
                    "capability": capability,
                    "grain": grain,
                    "slots": {"province": "江苏省", "city": None, "county": None, "sn": None},
                    "slot_confidence": {"province": "high", "time": "high"},
                    "slot_source": {"province": "explicit", "time": "explicit"},
                    "time_window": {"start_time": "2026-03-15 00:00:00", "end_time": "2026-04-13 23:59:59"},
                    "source_turn_id": 1,
                    "last_active_turn_id": 1,
                    "parent_target_key": None,
                }
            ],
            "result_refs": [],
            "action_targets": [],
        }

    async def test_closed_context_contextual_device_distribution_is_blocked(self) -> None:
        result = await self.service.resolve(
            text="那设备分布呢",
            current_context=self._base_data_context(closed=True),
            entities={"province": [], "city": [], "county": [], "sn": []},
            time_evidence=self._time_evidence(has_time_signal=False),
            turn_id=2,
        )

        self.assertEqual(result.conversation_state, "closed")
        self.assertEqual(result.follow_up_mode, "blocked")
        self.assertEqual(result.subject_family, "device_registry")
        self.assertEqual(result.answer_intent, "distribution")
        self.assertEqual(result.blocked_reason, "closed_context")

    async def test_subset_follow_up_keeps_group_answer_intent(self) -> None:
        result = await self.service.resolve(
            text="这些地区里只看睢宁县",
            current_context=self._base_data_context(capability="group", grain="region_group"),
            entities={"province": [], "city": [], "county": ["睢宁县"], "sn": []},
            time_evidence=self._time_evidence(has_time_signal=False),
            turn_id=2,
        )

        self.assertEqual(result.conversation_state, "open")
        self.assertEqual(result.follow_up_mode, "subset")
        self.assertEqual(result.subject_family, "soil")
        self.assertEqual(result.answer_intent, "group")
        self.assertEqual(result.data_focus, "all_records")
        self.assertIsNone(result.blocked_reason)

    async def test_compare_query_sets_compare_mode(self) -> None:
        result = await self.service.resolve(
            text="徐州和南通最近30天对比一下",
            current_context={},
            entities={"province": [], "city": ["徐州市", "南通市"], "county": [], "sn": []},
            time_evidence=self._time_evidence(
                has_time_signal=True,
                start_time="2026-03-15 00:00:00",
                end_time="2026-04-13 23:59:59",
            ),
            turn_id=1,
        )

        self.assertEqual(result.follow_up_mode, "standalone")
        self.assertEqual(result.subject_family, "soil")
        self.assertEqual(result.answer_intent, "compare")
        self.assertEqual(result.compare_mode, "entity_compare")

    async def test_warning_group_query_surfaces_warning_focus_and_measure(self) -> None:
        result = await self.service.resolve(
            text="最近30天有没有需要重点关注的地区",
            current_context={},
            entities={"province": [], "city": [], "county": [], "sn": []},
            time_evidence=self._time_evidence(
                has_time_signal=True,
                start_time="2026-03-15 00:00:00",
                end_time="2026-04-13 23:59:59",
            ),
            turn_id=1,
        )

        self.assertEqual(result.subject_family, "warning")
        self.assertEqual(result.answer_intent, "group")
        self.assertEqual(result.data_focus, "warning_only")
        self.assertEqual(result.measure, "alert_device_count")


if __name__ == "__main__":
    unittest.main()

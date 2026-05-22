"""Unit tests for ConsecutiveDroughtService."""

from __future__ import annotations

import unittest
from datetime import date
from typing import Any


class FakeSoilRepository:
    """Returns pre-built rows as if queried from MySQL."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def query_raw(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        return self._rows


class ConsecutiveDroughtServiceTest(unittest.TestCase):

    def _make_service(self, rows):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        return ConsecutiveDroughtService(soil_repository=FakeSoilRepository(rows))

    def test_returns_streaks_meeting_min_days(self):
        svc = self._make_service([
            {"city": "常州市", "county": "溧阳市", "streak_start": date(2026, 4, 11),
             "streak_end": date(2026, 4, 13), "consecutive_days": 3},
        ])
        result = svc.query(min_consecutive_days=3, window_days=30)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["city"], "常州市")
        self.assertEqual(result[0]["consecutive_days"], 3)

    def test_empty_when_no_streaks(self):
        svc = self._make_service([])
        result = svc.query(min_consecutive_days=3, window_days=30)
        self.assertEqual(result, [])

    def test_streaks_below_min_days_excluded(self):
        svc = self._make_service([
            {"city": "南京市", "county": "六合区", "streak_start": date(2026, 4, 1),
             "streak_end": date(2026, 4, 2), "consecutive_days": 2},
        ])
        result = svc.query(min_consecutive_days=3, window_days=30)
        self.assertEqual(result, [])

    def test_build_sql_contains_window_functions(self):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        sql = ConsecutiveDroughtService._build_sql(
            min_consecutive_days=3, window_days=30, warning_type="heavy_drought", region_filter=""
        )
        self.assertIn("ROW_NUMBER()", sql)
        self.assertIn("PARTITION BY", sql)
        self.assertIn("water20cm < 50", sql)
        self.assertIn("3", sql)

    def test_build_sql_waterlogging(self):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        sql = ConsecutiveDroughtService._build_sql(
            min_consecutive_days=2, window_days=30, warning_type="waterlogging", region_filter=""
        )
        self.assertIn("water20cm >= 150", sql)

    def test_build_sql_any_warning(self):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        sql = ConsecutiveDroughtService._build_sql(
            min_consecutive_days=3, window_days=30, warning_type=None, region_filter=""
        )
        self.assertIn("water20cm < 50", sql)
        self.assertIn("water20cm >= 150", sql)


if __name__ == "__main__":
    unittest.main()

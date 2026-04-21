from __future__ import annotations

"""Business-time resolver for soil data queries.

All relative phrases such as "最近", "最近7天", "现在", and "这一批" are resolved
against the latest business time/batch in MySQL, not the machine clock.  This
keeps answers reproducible when imported agriculture data lags wall-clock time.
"""

from datetime import datetime, timedelta
from typing import Any

from app.repositories.soil_repository import SoilRepository


class TimeResolveService:
    """Resolve finite time-window slots into concrete query boundaries."""

    def __init__(self, repository: SoilRepository):
        """Repository supplies latest business time and latest batch id."""
        self.repository = repository

    def resolve(
        self,
        *,
        slots: dict[str, Any],
        latest_business_time: str | None = None,
        latest_batch_id: str | None = None,
        timezone: str = "Asia/Shanghai",
    ) -> dict[str, Any]:
        """Return a normalized time bundle for the downstream query planner."""
        del timezone
        latest_business_time = latest_business_time or self.repository.latest_business_time()
        latest_batch_id = latest_batch_id or self.repository.latest_batch_id()
        resolved_time_range = slots.get("time_range", "last_7_days")
        latest_dt = self._parse_datetime(latest_business_time)
        payload = {
            "latest_business_time": latest_business_time,
            "latest_batch_id": latest_batch_id,
            "resolved_batch_id": latest_batch_id if slots.get("batch_id") == "latest_batch" else slots.get("batch_id"),
            "resolved_time_range": resolved_time_range,
            "resolution_mode": "latest_business_time",
            "time_basis": "latest_business_time",
            "start_time": latest_business_time,
            "end_time": latest_business_time,
        }
        if resolved_time_range == "last_7_days" and latest_dt:
            # Include the latest business date itself, so "last_7_days" is
            # latest day plus six prior days.
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    "start_time": self._format_datetime(latest_dt - timedelta(days=6)),
                    "end_time": self._format_datetime(latest_dt),
                }
            )
        elif resolved_time_range == "last_30_days" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "start_time": self._format_datetime(latest_dt - timedelta(days=29)),
                    "end_time": self._format_datetime(latest_dt),
                }
            )
        elif resolved_time_range == "last_week" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "start_time": self._format_datetime(latest_dt - timedelta(days=13)),
                    "end_time": self._format_datetime(latest_dt - timedelta(days=7)),
                }
            )
        elif resolved_time_range == "year_to_date" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "start_time": f"{latest_dt.year}-01-01 00:00:00",
                    "end_time": self._format_datetime(latest_dt),
                }
            )
        elif resolved_time_range in {"last_2_years", "last_3_years", "last_5_years"} and latest_dt:
            years = {"last_2_years": 730, "last_3_years": 1095, "last_5_years": 1825}[resolved_time_range]
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "start_time": self._format_datetime(latest_dt - timedelta(days=years - 1)),
                    "end_time": self._format_datetime(latest_dt),
                }
            )
        elif resolved_time_range == "exact_date" and slots.get("target_date"):
            payload.update(
                {
                    "resolution_mode": "exact_date",
                    "time_basis": "user_date",
                    "start_time": f"{slots['target_date']} 00:00:00",
                    "end_time": f"{slots['target_date']} 23:59:59",
                }
            )
        elif resolved_time_range == "latest_batch":
            # Batch mode should use batch_id filtering instead of sample_time
            # filtering; start/end are therefore intentionally null.
            payload.update(
                {
                    "resolution_mode": "latest_batch",
                    "time_basis": "latest_batch",
                    "start_time": None,
                    "end_time": None,
                }
            )
        elif resolved_time_range == "latest_business_time":
            payload.update(
                {
                    "resolution_mode": "latest_business_time",
                    "time_basis": "latest_business_time",
                    "start_time": latest_business_time,
                    "end_time": latest_business_time,
                }
            )
        return payload

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse the repository timestamp format into `datetime`."""
        if not value or value == "暂无":
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Format timestamps consistently for SQL filters and response payloads."""
        return value.strftime("%Y-%m-%d %H:%M:%S")


__all__ = ["TimeResolveService"]

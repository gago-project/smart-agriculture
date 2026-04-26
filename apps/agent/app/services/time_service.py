"""Business-time resolver for soil data queries.

All relative phrases such as "最近", "最近7天", "昨天", and "近12天" are resolved
against the latest business time in MySQL, not the machine clock.  This keeps
answers reproducible when imported agriculture data lags wall-clock time.
"""

from __future__ import annotations


import re
from datetime import datetime, time, timedelta
from typing import Any

from app.repositories.soil_repository import SoilRepository

LAST_N_DAYS_RANGE_RE = re.compile(r"^last_(\d+)_days$")
ANCHOR_BEFORE_RE = re.compile(r"^anchor_before_(\d+)_days$")
ANCHOR_AFTER_RE = re.compile(r"^anchor_after_(\d+)_days$")
N_DAYS_AGO_LABEL_RE = re.compile(r"^n_days_ago_(\d+)$")
RELATIVE_BEFORE_AT_AGO_RE = re.compile(r"^relative_before_(\d+)_at_(\d+)_ago$")


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
        timezone: str = "Asia/Shanghai",
        inherited_window: dict[str, Any] | None = None,
        inherit_resolved_window: bool = False,
    ) -> dict[str, Any]:
        """Return a normalized time bundle for the downstream query planner."""
        del timezone
        if inherit_resolved_window and inherited_window:
            return {
                "latest_business_time": latest_business_time or self.repository.latest_business_time(),
                "resolved_time_range": inherited_window.get("time_label") or slots.get("time_range") or "inherited_window",
                "resolution_mode": "inherited_window",
                "time_basis": "conversation_context",
                "start_time": inherited_window.get("start_time"),
                "end_time": inherited_window.get("end_time"),
            }
        latest_business_time = latest_business_time or self.repository.latest_business_time()
        resolved_time_range = slots.get("time_range") or "last_7_days"
        latest_dt = self._parse_datetime(latest_business_time)
        payload = {
            "latest_business_time": latest_business_time,
            "resolved_time_range": resolved_time_range,
            "resolution_mode": "latest_business_time",
            "time_basis": "latest_business_time",
            "start_time": latest_business_time,
            "end_time": latest_business_time,
        }
        dynamic_days = self._parse_last_n_days(resolved_time_range)
        if resolved_time_range == "today" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._day_window(latest_dt, days=1),
                }
            )
        elif resolved_time_range == "yesterday" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._offset_day_window(latest_dt, day_offset=1),
                }
            )
        elif resolved_time_range == "day_before_yesterday" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._offset_day_window(latest_dt, day_offset=2),
                }
            )
        elif resolved_time_range == "last_week" and latest_dt:
            current_monday = latest_dt.date() - timedelta(days=latest_dt.weekday())
            last_monday = current_monday - timedelta(days=7)
            last_sunday = current_monday - timedelta(days=1)
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    "start_time": self._format_datetime(datetime.combine(last_monday, time.min)),
                    "end_time": self._format_datetime(datetime.combine(last_sunday, time.max.replace(microsecond=0))),
                }
            )
        elif resolved_time_range == "year_to_date" and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    "start_time": f"{latest_dt.year}-01-01 00:00:00",
                    "end_time": self._format_datetime(self._end_of_day(latest_dt)),
                }
            )
        elif resolved_time_range in {"last_2_years", "last_3_years", "last_5_years"} and latest_dt:
            years = {"last_2_years": 730, "last_3_years": 1095, "last_5_years": 1825}[resolved_time_range]
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._day_window(latest_dt, days=years),
                }
            )
        elif (anchor_before_match := ANCHOR_BEFORE_RE.match(resolved_time_range)) and slots.get("target_date"):
            n = int(anchor_before_match.group(1))
            anchor_dt = self._parse_date(slots.get("target_date"))
            payload.update({
                "resolution_mode": "anchor_window",
                "time_basis": "anchor_date",
                **self._day_window(anchor_dt, days=n),
            })
        elif (anchor_after_match := ANCHOR_AFTER_RE.match(resolved_time_range)) and slots.get("target_date"):
            n = int(anchor_after_match.group(1))
            anchor_dt = self._parse_date(slots.get("target_date"))
            payload.update({
                "resolution_mode": "anchor_window",
                "time_basis": "anchor_date",
                "start_time": self._format_datetime(self._start_of_day(anchor_dt)),
                "end_time": self._format_datetime(self._end_of_day(anchor_dt + timedelta(days=n - 1))),
            })
        elif (m := N_DAYS_AGO_LABEL_RE.match(resolved_time_range)) and latest_dt:
            n = int(m.group(1))
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._offset_day_window(latest_dt, day_offset=n),
                }
            )
        elif (m := RELATIVE_BEFORE_AT_AGO_RE.match(resolved_time_range)) and latest_dt:
            before_days = int(m.group(1))
            n_ago = int(m.group(2))
            anchor = latest_dt - timedelta(days=n_ago)
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._day_window(anchor, days=before_days),
                }
            )
        elif dynamic_days and latest_dt:
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._day_window(latest_dt, days=dynamic_days),
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

    @classmethod
    def _parse_last_n_days(cls, value: str | None) -> int | None:
        """Parse canonical `last_N_days` labels."""
        if not value:
            return None
        match = LAST_N_DAYS_RANGE_RE.match(value)
        if not match:
            return None
        return max(int(match.group(1)), 1)

    @classmethod
    def _day_window(cls, latest_dt: datetime, *, days: int) -> dict[str, str]:
        """Return an inclusive natural-day window ending on latest business date."""
        start = cls._start_of_day(latest_dt - timedelta(days=days - 1))
        end = cls._end_of_day(latest_dt)
        return {"start_time": cls._format_datetime(start), "end_time": cls._format_datetime(end)}

    @classmethod
    def _offset_day_window(cls, latest_dt: datetime, *, day_offset: int) -> dict[str, str]:
        """Return one whole natural day offset from latest business date."""
        target = latest_dt - timedelta(days=day_offset)
        return {"start_time": cls._format_datetime(cls._start_of_day(target)), "end_time": cls._format_datetime(cls._end_of_day(target))}

    @staticmethod
    def _start_of_day(value: datetime) -> datetime:
        """Return midnight for the date of `value`."""
        return datetime.combine(value.date(), time.min)

    @staticmethod
    def _end_of_day(value: datetime) -> datetime:
        """Return 23:59:59 for the date of `value`."""
        return datetime.combine(value.date(), time.max.replace(microsecond=0))

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        """Parse a bare YYYY-MM-DD anchor date into a datetime at midnight."""
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None

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

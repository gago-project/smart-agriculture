"""Deterministic time-window parsing for soil-moisture queries."""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta


_CHINESE_NUMBERS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

_ABSOLUTE_TIME_PATTERNS = (
    re.compile(r"\d{4}-\d{1,2}-\d{1,2}"),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}"),
    re.compile(r"\d{1,2}月\d{1,2}日"),
    re.compile(r"\d{4}年\d{1,2}月"),
    re.compile(r"去年\d{1,2}月"),
)

_AMBIGUOUS_PATTERNS = (
    re.compile(r"这几天"),
    re.compile(r"半个月"),
    re.compile(r"半年"),
)


@dataclass(frozen=True)
class TimeWindowResolution:
    matched: bool = False
    has_time_signal: bool = False
    time_source: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    clarify_reason: str = ""


class TimeWindowService:
    """Resolve relative Chinese time expressions into absolute time windows."""

    def resolve(self, user_text: str, latest_business_time: str | None) -> TimeWindowResolution:
        text = (user_text or "").strip()
        if not text:
            return TimeWindowResolution()

        if any(pattern.search(text) for pattern in _AMBIGUOUS_PATTERNS):
            return TimeWindowResolution(has_time_signal=True, clarify_reason="ambiguous_time")

        if self._has_absolute_time_signal(text):
            return TimeWindowResolution(has_time_signal=True)

        anchor = self._parse_anchor(latest_business_time)
        relative_match = self._resolve_relative(text, anchor)
        if relative_match is not None:
            return relative_match

        return TimeWindowResolution()

    @staticmethod
    def _parse_anchor(latest_business_time: str | None) -> datetime | None:
        if not latest_business_time:
            return None
        try:
            return datetime.strptime(latest_business_time[:19], "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _has_absolute_time_signal(text: str) -> bool:
        return any(pattern.search(text) for pattern in _ABSOLUTE_TIME_PATTERNS)

    def _resolve_relative(self, text: str, anchor: datetime | None) -> TimeWindowResolution | None:
        if any(token in text for token in ("今天", "现在")):
            return self._anchor_required(anchor) or self._window("rule_relative", self._day(anchor, 0), self._day(anchor, 0, end=True))
        if "昨天" in text:
            return self._anchor_required(anchor) or self._window("rule_relative", self._day(anchor, -1), self._day(anchor, -1, end=True))
        if "前天" in text:
            return self._anchor_required(anchor) or self._window("rule_relative", self._day(anchor, -2), self._day(anchor, -2, end=True))
        if "这周" in text or "本周" in text:
            return self._anchor_required(anchor) or self._this_week(anchor)
        if "上周" in text:
            return self._anchor_required(anchor) or self._last_week(anchor)
        if "这个月" in text or "本月" in text:
            return self._anchor_required(anchor) or self._this_month(anchor)
        if "上月" in text or "一个月" in text:
            return self._anchor_required(anchor) or self._last_month(anchor)
        if "近一年" in text or "最近1年" in text:
            return self._anchor_required(anchor) or self._rolling_days(anchor, 365)

        for pattern, unit in (
            (re.compile(r"(?:最近|近|过去|前)\s*([0-9一二两三四五六七八九十百]+)\s*天"), "days"),
            (re.compile(r"(?:最近|近|过去)\s*([0-9一二两三四五六七八九十百]+)\s*周"), "weeks"),
            (re.compile(r"(?:最近|近)\s*([0-9一二两三四五六七八九十百]+)\s*(?:个)?月"), "months"),
            (re.compile(r"([0-9一二两三四五六七八九十百]+)\s*周"), "weeks"),
            (re.compile(r"([0-9一二两三四五六七八九十百]+)\s*(?:个)?月"), "months"),
        ):
            match = pattern.search(text)
            if not match:
                continue
            count = self._parse_number(match.group(1))
            if count is None:
                return TimeWindowResolution(has_time_signal=True, clarify_reason="ambiguous_time")
            if count <= 0:
                return TimeWindowResolution(has_time_signal=True, clarify_reason="invalid_time_range")
            if anchor is None:
                return TimeWindowResolution(has_time_signal=True, clarify_reason="missing_latest_business_time")
            if unit == "days":
                return self._rolling_days(anchor, count)
            if unit == "weeks":
                return self._rolling_days(anchor, count * 7)
            return self._rolling_months(anchor, count)

        return None

    @staticmethod
    def _anchor_required(anchor: datetime | None) -> TimeWindowResolution | None:
        if anchor is None:
            return TimeWindowResolution(has_time_signal=True, clarify_reason="missing_latest_business_time")
        return None

    @staticmethod
    def _parse_number(raw: str) -> int | None:
        if raw.isdigit():
            return int(raw)
        if raw == "十":
            return 10
        if "十" in raw:
            head, _, tail = raw.partition("十")
            tens = _CHINESE_NUMBERS.get(head, 1 if head == "" else None)
            ones = _CHINESE_NUMBERS.get(tail, 0 if tail == "" else None)
            if tens is None or ones is None:
                return None
            return tens * 10 + ones
        total = 0
        for char in raw:
            value = _CHINESE_NUMBERS.get(char)
            if value is None:
                return None
            total = total * 10 + value
        return total

    @staticmethod
    def _fmt(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _window(cls, time_source: str, start: datetime, end: datetime) -> TimeWindowResolution:
        return TimeWindowResolution(
            matched=True,
            has_time_signal=True,
            time_source=time_source,
            start_time=cls._fmt(start),
            end_time=cls._fmt(end),
        )

    @staticmethod
    def _day(anchor: datetime, offset: int, *, end: bool = False) -> datetime:
        date_value = anchor.date() + timedelta(days=offset)
        hour, minute, second = (23, 59, 59) if end else (0, 0, 0)
        return datetime(date_value.year, date_value.month, date_value.day, hour, minute, second)

    def _rolling_days(self, anchor: datetime, days: int) -> TimeWindowResolution:
        start = self._day(anchor, -(days - 1))
        end = self._day(anchor, 0, end=True)
        return self._window("rule_relative", start, end)

    def _rolling_months(self, anchor: datetime, months: int) -> TimeWindowResolution:
        year = anchor.year
        month = anchor.month - (months - 1)
        while month <= 0:
            month += 12
            year -= 1
        start = datetime(year, month, 1, 0, 0, 0)
        end = self._day(anchor, 0, end=True)
        return self._window("rule_relative", start, end)

    def _this_week(self, anchor: datetime) -> TimeWindowResolution:
        start = self._day(anchor, -anchor.weekday())
        end = self._day(anchor, 0, end=True)
        return self._window("rule_relative", start, end)

    def _last_week(self, anchor: datetime) -> TimeWindowResolution:
        last_sunday = anchor.date() - timedelta(days=anchor.weekday() + 1)
        last_monday = last_sunday - timedelta(days=6)
        start = datetime(last_monday.year, last_monday.month, last_monday.day, 0, 0, 0)
        end = datetime(last_sunday.year, last_sunday.month, last_sunday.day, 23, 59, 59)
        return self._window("rule_relative", start, end)

    def _this_month(self, anchor: datetime) -> TimeWindowResolution:
        start = datetime(anchor.year, anchor.month, 1, 0, 0, 0)
        end = self._day(anchor, 0, end=True)
        return self._window("rule_relative", start, end)

    def _last_month(self, anchor: datetime) -> TimeWindowResolution:
        if anchor.month == 1:
            year = anchor.year - 1
            month = 12
        else:
            year = anchor.year
            month = anchor.month - 1
        last_day = calendar.monthrange(year, month)[1]
        start = datetime(year, month, 1, 0, 0, 0)
        end = datetime(year, month, last_day, 23, 59, 59)
        return self._window("rule_relative", start, end)


__all__ = ["TimeWindowService", "TimeWindowResolution"]

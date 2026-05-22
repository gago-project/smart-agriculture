"""Query regions with consecutive drought days using gaps-and-islands SQL."""

from __future__ import annotations

from typing import Any


_HEAVY_DROUGHT_PREDICATE = (
    "water20cm < 50 AND NOT (water20cm = 0 AND t20cm = 0)"
)
_WATERLOGGING_PREDICATE = "water20cm >= 150"
_ANY_WARNING_PREDICATE = (
    "(water20cm < 50 AND NOT (water20cm = 0 AND t20cm = 0)) OR water20cm >= 150"
)


def _warning_predicate(warning_type: str | None) -> str:
    if warning_type == "heavy_drought":
        return _HEAVY_DROUGHT_PREDICATE
    if warning_type == "waterlogging":
        return _WATERLOGGING_PREDICATE
    return _ANY_WARNING_PREDICATE


class ConsecutiveDroughtService:
    """Find city/county regions with consecutive drought days."""

    def __init__(self, soil_repository: Any) -> None:
        self._repo = soil_repository

    def query(
        self,
        *,
        min_consecutive_days: int = 3,
        window_days: int = 30,
        warning_type: str | None = "heavy_drought",
        city_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        region_filter = f"AND city = '{city_filter}'" if city_filter else ""
        sql = self._build_sql(
            min_consecutive_days=min_consecutive_days,
            window_days=window_days,
            warning_type=warning_type,
            region_filter=region_filter,
        )
        rows = self._repo.query_raw(sql, ())
        return [
            r for r in rows
            if int(r.get("consecutive_days") or 0) >= min_consecutive_days
        ]

    @staticmethod
    def _build_sql(
        *,
        min_consecutive_days: int,
        window_days: int,
        warning_type: str | None,
        region_filter: str,
    ) -> str:
        predicate = _warning_predicate(warning_type)
        return f"""
WITH daily_drought AS (
  SELECT
    city,
    county,
    DATE(create_time) AS day,
    SUM(CASE WHEN {predicate} THEN 1 ELSE 0 END) AS drought_device_count
  FROM fact_soil_moisture
  WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL {window_days} DAY)
    {region_filter}
  GROUP BY city, county, DATE(create_time)
  HAVING drought_device_count > 0
),
numbered AS (
  SELECT
    city, county, day,
    DATE_SUB(day, INTERVAL ROW_NUMBER() OVER (
      PARTITION BY city, county ORDER BY day
    ) DAY) AS grp
  FROM daily_drought
),
streaks AS (
  SELECT
    city, county,
    MIN(day) AS streak_start,
    MAX(day) AS streak_end,
    COUNT(*) AS consecutive_days
  FROM numbered
  GROUP BY city, county, grp
)
SELECT city, county, streak_start, streak_end, consecutive_days
FROM streaks
WHERE consecutive_days >= {min_consecutive_days}
ORDER BY consecutive_days DESC, streak_end DESC
"""

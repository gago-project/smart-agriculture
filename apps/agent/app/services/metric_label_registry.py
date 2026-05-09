"""Canonical metric labels for deterministic soil answers."""

from __future__ import annotations

FIELD_METRIC_LABELS: dict[str, str] = {
    "record_count": "墒情记录",
    "soil_record_count": "墒情记录",
    "alert_record_count": "预警记录",
    "warning_record_count": "预警记录",
    "device_count": "墒情仪",
    "alert_device_count": "预警墒情仪",
    "region_count": "地区",
    "alert_region_count": "预警地区",
}

COMPARE_METRIC_LABELS: dict[str, str] = {
    "record_count": "墒情记录数",
    "alert_record_count": "预警记录数",
    "device_count": "墒情仪数量",
    "alert_device_count": "预警墒情仪数量",
    "region_count": "地区数",
    "alert_region_count": "预警地区数",
}

METRIC_UNITS: dict[str, str] = {
    "record_count": "条",
    "soil_record_count": "条",
    "alert_record_count": "条",
    "warning_record_count": "条",
    "device_count": "套",
    "alert_device_count": "套",
    "region_count": "个",
    "alert_region_count": "个",
}


def field_metric_label(metric: str | None) -> str:
    return FIELD_METRIC_LABELS.get(str(metric or ""), "")


def compare_metric_label(metric: str | None) -> str:
    return COMPARE_METRIC_LABELS.get(str(metric or ""), "")


def metric_unit(metric: str | None) -> str:
    return METRIC_UNITS.get(str(metric or ""), "")


__all__ = [
    "FIELD_METRIC_LABELS",
    "COMPARE_METRIC_LABELS",
    "METRIC_UNITS",
    "field_metric_label",
    "compare_metric_label",
    "metric_unit",
]

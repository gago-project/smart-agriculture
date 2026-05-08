"""Post-response fact-check for deterministic soil query answers.

Operates in warning mode: logs inconsistencies but never blocks responses.
Checks numeric consistency between DB-derived block metrics and rendered final_text,
plus existence integrity (text doesn't claim data when blocks show empty).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

# Metric key → (Chinese label in text, unit suffix)
_METRIC_CHECKS: list[tuple[str, str, str]] = [
    ("record_count", "记录", "条"),
    ("device_count", "墒情仪", "套"),
    ("region_count", "地区", "个"),
]

# Positive-existence phrases that should not appear when record_count == 0
_EXISTENCE_PHRASES = re.compile(
    r"(\d+)\s*条|(\d+)\s*套|共\s*(\d+)|监测到\s*(\d+)"
)


@dataclass
class FactCheckResult:
    passed: bool
    failures: list[str] = field(default_factory=list)


class FactCheckService:
    """Warning-mode structural fact checker for business responses."""

    # Only these block types carry a metrics dict that is consistently checkable
    _METRICS_BLOCK_TYPES = {"summary_card", "detail_card", "ranking_card"}

    def verify(self, response: dict) -> FactCheckResult:
        if response.get("answer_kind") != "business":
            return FactCheckResult(passed=True)
        blocks = response.get("blocks") or []
        if not blocks:
            return FactCheckResult(passed=True)
        block = blocks[0]
        if block.get("block_type") not in self._METRICS_BLOCK_TYPES:
            return FactCheckResult(passed=True)
        final_text = str(response.get("final_text") or "")
        if not final_text:
            return FactCheckResult(passed=True)

        failures: list[str] = []
        failures.extend(self._check_numeric_consistency(final_text, block))
        failures.extend(self._check_existence_integrity(final_text, block))

        if failures:
            logger.warning(
                "fact_check_warning capability=%s failures=%s",
                response.get("capability"),
                failures,
            )
            return FactCheckResult(passed=False, failures=failures)
        return FactCheckResult(passed=True)

    @staticmethod
    def _check_numeric_consistency(final_text: str, block: dict) -> list[str]:
        """Verify that key count metrics from block.metrics appear in final_text."""
        metrics = block.get("metrics") or {}
        failures: list[str] = []
        for metric_key, label, suffix in _METRIC_CHECKS:
            value = metrics.get(metric_key)
            if value is None:
                continue
            value_int = int(value)
            if value_int == 0:
                continue
            # Accept if the number+suffix appears near the label, or the number appears anywhere
            exact = re.compile(
                rf"{re.escape(label)}[：:]\s*{value_int}{re.escape(suffix)}"
            )
            if not exact.search(final_text) and str(value_int) not in final_text:
                failures.append(
                    f"metric {metric_key}={value_int} missing from final_text"
                )
        return failures

    @staticmethod
    def _check_existence_integrity(final_text: str, block: dict) -> list[str]:
        """Verify the text doesn't claim positive counts when record_count is 0."""
        metrics = block.get("metrics") or {}
        record_count = int(metrics.get("record_count") or 0)
        if record_count > 0:
            return []
        matches = _EXISTENCE_PHRASES.findall(final_text)
        positive = [
            g for groups in matches for g in groups if g and float(g) > 0
        ]
        if positive:
            return [
                f"record_count=0 but final_text contains positive count(s): {positive}"
            ]
        return []


__all__ = ["FactCheckResult", "FactCheckService"]

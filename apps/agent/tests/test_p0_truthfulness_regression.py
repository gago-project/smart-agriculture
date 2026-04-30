"""P0 truthfulness regression suite.

Covers:
  1. Raw-only query results: no fabricated status/risk fields leak into query outputs.
  2. Entity normalization: common short-form city names → canonical.
  3. Deterministic time window resolution: relative Chinese time phrases expand correctly.
  4. Empty-result diagnosis: three distinct paths (normalize_failed / entity_not_found / no_data_in_window).
  5. FactCheck alert-mode: numeric value out of range produces a warning (not a block).
  6. FactCheck blocking: value not in tool result blocks with failed=True.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.fact_check_service import FactCheckService
from app.services.parameter_resolver_service import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    ParameterResolverService,
)
from app.services.time_window_service import TimeWindowService
from app.services.tool_executor_service import ToolExecutorService

_LBT = "2026-04-20 12:00:00"
_WINDOW = {
    "start_time": "2026-04-20 00:00:00",
    "end_time": "2026-04-20 23:59:59",
}


# ── 1. Raw-only truthfulness ───────────────────────────────────────────────────

class TestRawOnlyTruthfulness:
    @pytest.mark.asyncio
    async def test_summary_result_contains_only_raw_metrics(self):
        repo = MagicMock()
        repo.filter_records_async = AsyncMock(
            return_value=[
                {
                    "sn": "SNS00204333",
                    "city": "南通市",
                    "county": "如东县",
                    "create_time": "2026-04-20 10:00:00",
                    "water20cm": 42.5,
                }
            ]
        )
        executor = ToolExecutorService(repository=repo)

        result = await executor.execute(
            tool_name="query_soil_summary",
            tool_args={"start_time": "2026-04-20 00:00:00", "end_time": "2026-04-20 23:59:59"},
        )

        assert result["total_records"] == 1
        assert result["device_count"] == 1
        assert result["region_count"] == 1
        for banned_key in ("soil_status", "warning_level", "risk_score", "display_label", "rule_version", "alert_count"):
            assert banned_key not in result

    @pytest.mark.asyncio
    async def test_detail_latest_record_does_not_contain_derived_fields(self):
        repo = MagicMock()
        repo.filter_records_async = AsyncMock(
            return_value=[
                {
                    "sn": "SNS00204333",
                    "city": "南通市",
                    "county": "如东县",
                    "create_time": "2026-04-20 10:00:00",
                    "water20cm": 42.5,
                    "t20cm": 18.2,
                }
            ]
        )
        executor = ToolExecutorService(repository=repo)

        result = await executor.execute(
            tool_name="query_soil_detail",
            tool_args={"start_time": "2026-04-20 00:00:00", "end_time": "2026-04-20 23:59:59"},
        )

        latest_record = result["latest_record"]
        for banned_key in ("soil_status", "warning_level", "risk_score", "display_label", "rule_version"):
            assert banned_key not in latest_record


# ── 2. Entity normalization ────────────────────────────────────────────────────

class TestEntityNormalization:
    """Uses an in-memory alias index (no DB)."""

    _ALIAS_ROWS = [
        {
            "alias_name": "南通",
            "canonical_name": "南通市",
            "region_level": "city",
            "parent_city_name": None,
            "alias_source": "generated_fact",
        },
        {
            "alias_name": "南通市",
            "canonical_name": "南通市",
            "region_level": "city",
            "parent_city_name": None,
            "alias_source": "canonical",
        },
        {
            "alias_name": "如东",
            "canonical_name": "如东县",
            "region_level": "county",
            "parent_city_name": "南通市",
            "alias_source": "generated_fact",
        },
        {
            "alias_name": "如东县",
            "canonical_name": "如东县",
            "region_level": "county",
            "parent_city_name": "南通市",
            "alias_source": "canonical",
        },
    ]

    def _resolver(self):
        svc = ParameterResolverService()
        svc._alias_index = svc._build_alias_index(self._ALIAS_ROWS)
        return svc

    def test_city_alias_normalized(self):
        svc = self._resolver()
        canon, conf = svc._normalize_name("南通", svc._alias_index, expected_level="city")
        assert canon == "南通市"
        assert conf == CONFIDENCE_MEDIUM

    def test_county_alias_normalized(self):
        svc = self._resolver()
        canon, conf = svc._normalize_name("如东", svc._alias_index, expected_level="county")
        assert canon == "如东县"
        assert conf == CONFIDENCE_MEDIUM

    def test_known_canonical_name_is_high_confidence(self):
        svc = self._resolver()
        canon, conf = svc._normalize_name("南通市", svc._alias_index, expected_level="city")
        assert canon == "南通市"
        assert conf == CONFIDENCE_HIGH

    def test_unknown_name_low_confidence(self):
        svc = self._resolver()
        canon, conf = svc._normalize_name("火星城", svc._alias_index, expected_level="city")
        assert conf == CONFIDENCE_LOW

    @pytest.mark.asyncio
    async def test_sn_valid_format(self):
        svc = self._resolver()
        raw_args = {"sn": "sns00204333", **_WINDOW}
        outcome = await svc._resolve_entities(raw_args, svc._alias_index)
        assert outcome.resolved_args["sn"] == "SNS00204333"
        assert outcome.confidence == CONFIDENCE_HIGH

    @pytest.mark.asyncio
    async def test_sn_invalid_format_medium(self):
        svc = self._resolver()
        raw_args = {"sn": "BADFORMAT123", **_WINDOW}
        outcome = await svc._resolve_entities(raw_args, svc._alias_index)
        assert outcome.confidence == CONFIDENCE_MEDIUM
        assert outcome.should_clarify is False
        assert any("格式不符" in w for w in outcome.warnings)


# ── 3. Deterministic time window resolution ───────────────────────────────────

class TestTimeExpansion:
    _SVC = TimeWindowService()

    def test_recent_7_days_range(self):
        lbt = "2026-04-20 12:00:00"
        result = self._SVC.resolve("最近7天墒情怎么样", lbt)
        start_dt = datetime.strptime(result.start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(result.end_time, "%Y-%m-%d %H:%M:%S")
        anchor = datetime(2026, 4, 20)
        assert start_dt.date() == (anchor - timedelta(days=6)).date()
        assert end_dt.date() == anchor.date()

    def test_today(self):
        lbt = "2026-04-20 08:00:00"
        result = self._SVC.resolve("今天墒情怎么样", lbt)
        assert result.start_time == "2026-04-20 00:00:00"
        assert result.end_time == "2026-04-20 23:59:59"

    def test_last_month_january_rollover(self):
        lbt = "2026-01-15 00:00:00"
        result = self._SVC.resolve("上月墒情怎么样", lbt)
        assert result.start_time.startswith("2025-12-01")
        assert result.end_time.startswith("2025-12-31")

    def test_last_week_full_mon_sun(self):
        # 2026-04-20 is Monday; last_week = 2026-04-13 (Mon) to 2026-04-19 (Sun)
        lbt = "2026-04-20 00:00:00"
        result = self._SVC.resolve("上周墒情怎么样", lbt)
        assert result.start_time.startswith("2026-04-13")
        assert result.end_time.startswith("2026-04-19")

    def test_ambiguous_phrase_requires_clarification(self):
        result = self._SVC.resolve("这几天墒情怎么样", _LBT)
        assert result.matched is False
        assert result.has_time_signal is True
        assert result.clarify_reason == "ambiguous_time"


# ── 4. Empty-result diagnosis ──────────────────────────────────────────────────

class TestEmptyResultDiagnosis:
    def _make_executor(self, *, device_count=0, region_count=0) -> ToolExecutorService:
        repo = MagicMock()
        repo.device_record_count_async = AsyncMock(return_value=device_count)
        repo.region_record_count_async = AsyncMock(return_value=region_count)
        return ToolExecutorService(repository=repo)

    @pytest.mark.asyncio
    async def test_normalize_failed_when_low_confidence(self):
        svc = self._make_executor()
        path = await svc._auto_diagnose_empty({"city": "未知城市"}, entity_confidence="low")
        assert path == "normalize_failed"

    @pytest.mark.asyncio
    async def test_entity_not_found_for_missing_device(self):
        svc = self._make_executor(device_count=0)
        path = await svc._auto_diagnose_empty({"sn": "SNS99999999"}, entity_confidence="high")
        assert path == "entity_not_found"

    @pytest.mark.asyncio
    async def test_no_data_in_window_when_device_exists(self):
        svc = self._make_executor(device_count=5)
        path = await svc._auto_diagnose_empty({"sn": "SNS00204333"}, entity_confidence="high")
        assert path == "no_data_in_window"

    @pytest.mark.asyncio
    async def test_entity_not_found_for_missing_region(self):
        svc = self._make_executor(region_count=0)
        path = await svc._auto_diagnose_empty({"city": "如东县"}, entity_confidence="high")
        assert path == "entity_not_found"

    @pytest.mark.asyncio
    async def test_no_data_in_window_for_existing_region(self):
        svc = self._make_executor(region_count=10)
        path = await svc._auto_diagnose_empty({"city": "南通市"}, entity_confidence="high")
        assert path == "no_data_in_window"


# ── 5. FactCheck alert-mode: numeric out of range → warning only ───────────────

class TestFactCheckAlertMode:
    _SVC = FactCheckService()

    def _bundle(self, text: str) -> dict:
        return {"final_answer": text}

    def test_numeric_out_of_range_produces_warning_not_block(self):
        qt = {"avg_water20cm": 45.0}
        result = self._SVC.verify(
            answer_type="soil_summary_answer",
            answer_bundle=self._bundle("该地区含水量约为 99.9%，情况良好。"),
            query_result=qt,
            tool_trace=[{"result": qt}],
            answer_facts={"total_records": 1},
            resolved_args={"start_time": "2026-04-14 00:00:00", "end_time": "2026-04-20 23:59:59"},
        )
        assert result["failed"] is False
        assert any("数值核验" in w for w in result["warnings"])

    def test_numeric_in_range_no_warning(self):
        qt = {"avg_water20cm": 45.0}
        result = self._SVC.verify(
            answer_type="soil_summary_answer",
            answer_bundle=self._bundle("该地区含水量约为 45%。"),
            query_result=qt,
            tool_trace=[{"result": qt}],
            answer_facts={"total_records": 1},
            resolved_args={"start_time": "2026-04-14 00:00:00", "end_time": "2026-04-20 23:59:59"},
        )
        assert result["failed"] is False
        assert not any("数值核验" in w for w in result["warnings"])

    def test_rank_ordinal_wrong_entity_warns(self):
        qt = {"items": [{"name": "如东县", "rank": 1}, {"name": "海安市", "rank": 2}]}
        result = self._SVC.verify(
            answer_type="soil_ranking_answer",
            answer_bundle=self._bundle("排名第1名的是海安市，情况最严重。"),
            query_result=qt,
            tool_trace=[{"result": qt}],
            answer_facts={"items": qt["items"]},
            resolved_args={},
        )
        assert result["failed"] is False
        assert any("排名核验" in w for w in result["warnings"])


# ── 6. FactCheck blocking: entity missing from answer ──────────────────────────

class TestFactCheckBlocking:
    _SVC = FactCheckService()

    def test_entity_name_missing_blocks(self):
        result = self._SVC.verify(
            answer_type="soil_detail_answer",
            answer_bundle={"final_answer": "该地区土壤含水量正常。"},
            query_result={},
            tool_trace=[{"result": {"record_count": 3}}],
            answer_facts={"entity_name": "如东县", "record_count": 3},
        )
        assert result["failed"] is True
        assert result["need_retry"] is True

    def test_no_data_contradiction_blocks(self):
        qt = {"total_records": 10}
        result = self._SVC.verify(
            answer_type="soil_summary_answer",
            answer_bundle={"final_answer": "查询范围内无数据，无法回答。"},
            query_result=qt,
            tool_trace=[{"result": qt}],
            answer_facts={"total_records": 10},
        )
        assert result["failed"] is True

    def test_empty_answer_blocks(self):
        result = self._SVC.verify(
            answer_type="soil_summary_answer",
            answer_bundle={"final_answer": ""},
            query_result={},
            tool_trace=[],
            answer_facts={},
        )
        assert result["failed"] is True
        assert result["need_retry"] is False

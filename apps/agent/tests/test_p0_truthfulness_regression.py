"""P0 truthfulness regression suite.

Covers:
  1. Rule thresholds: feature flag on/off produces consistent status judgments.
  2. Entity normalization: common short-form city names → canonical.
  3. Time expression expansion: last_7_days within expected range.
  4. Empty-result diagnosis: three distinct paths (normalize_failed / entity_not_found / no_data_in_window).
  5. FactCheck alert-mode: numeric value out of range produces a warning (not a block).
  6. FactCheck blocking: value not in tool result blocks with failed=True.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.rule_repository import RuleRepository, SoilRuleProfile
from app.repositories.soil_repository import _evaluate_record_status
from app.services.fact_check_service import FactCheckService
from app.services.parameter_resolver_service import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    ParameterResolverService,
    _expand_time_expression,
)
from app.services.tool_executor_service import ToolExecutorService


# ── helpers ────────────────────────────────────────────────────────────────────

def _profile(heavy_drought_max: float = 20.0, waterlogging_min: float = 80.0) -> SoilRuleProfile:
    return SoilRuleProfile(
        rule_name="soil_warning_v1",
        heavy_drought_max=heavy_drought_max,
        waterlogging_min=waterlogging_min,
        device_fault_water20=0.0,
        device_fault_t20=0.0,
        rule_version="test@2026-01-01T00:00:00",
    )


_LBT = "2026-04-20 12:00:00"


# ── 1. Rule threshold feature-flag consistency ─────────────────────────────────

class TestRuleThresholds:
    def test_hardcoded_heavy_drought(self):
        record = {"water20cm": 15.0, "water40cm": 15.0}
        result = _evaluate_record_status(record, rule_profile=_profile())
        assert result["soil_status"] == "heavy_drought"

    def test_hardcoded_waterlogging(self):
        record = {"water20cm": 85.0, "water40cm": 85.0}
        result = _evaluate_record_status(record, rule_profile=_profile())
        assert result["soil_status"] == "waterlogging"

    def test_normal_status(self):
        record = {"water20cm": 50.0, "water40cm": 50.0}
        result = _evaluate_record_status(record, rule_profile=_profile())
        assert result["soil_status"] not in ("heavy_drought", "waterlogging", "device_fault")

    def test_custom_threshold_changes_judgment(self):
        # Raise heavy_drought_max so 25% is now drought
        record = {"water20cm": 25.0, "water40cm": 25.0}
        default_result = _evaluate_record_status(record, rule_profile=_profile(heavy_drought_max=20.0))
        custom_result = _evaluate_record_status(record, rule_profile=_profile(heavy_drought_max=30.0))
        assert default_result["soil_status"] != "heavy_drought"
        assert custom_result["soil_status"] == "heavy_drought"

    def test_rule_version_included(self):
        record = {"water20cm": 50.0}
        result = _evaluate_record_status(record, rule_profile=_profile())
        assert "rule_version" in result
        assert result["rule_version"] == "test@2026-01-01T00:00:00"


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
        assert conf == CONFIDENCE_HIGH

    def test_county_alias_normalized(self):
        svc = self._resolver()
        canon, conf = svc._normalize_name("如东", svc._alias_index, expected_level="county")
        assert canon == "如东县"
        assert conf == CONFIDENCE_HIGH

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
        raw_args = {"sn": "sns00204333", "time_expression": "today"}
        outcome = await svc._resolve_entities(raw_args, svc._alias_index)
        assert outcome.resolved_args["sn"] == "SNS00204333"
        assert outcome.confidence == CONFIDENCE_HIGH

    @pytest.mark.asyncio
    async def test_sn_invalid_format_medium(self):
        svc = self._resolver()
        raw_args = {"sn": "BADFORMAT123", "time_expression": "today"}
        outcome = await svc._resolve_entities(raw_args, svc._alias_index)
        assert outcome.confidence == CONFIDENCE_MEDIUM
        assert any("格式不符" in w for w in outcome.warnings)


# ── 3. Time expression expansion ──────────────────────────────────────────────

class TestTimeExpansion:
    def test_last_7_days_range(self):
        lbt = "2026-04-20 12:00:00"
        start, end = _expand_time_expression("last_7_days", lbt)
        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
        anchor = datetime(2026, 4, 20)
        assert start_dt.date() == (anchor - timedelta(days=6)).date()
        assert end_dt.date() == anchor.date()

    def test_today(self):
        lbt = "2026-04-20 08:00:00"
        start, end = _expand_time_expression("today", lbt)
        assert start == "2026-04-20 00:00:00"
        assert end == "2026-04-20 23:59:59"

    def test_last_month_january_rollover(self):
        lbt = "2026-01-15 00:00:00"
        start, end = _expand_time_expression("last_month", lbt)
        assert start.startswith("2025-12-01")
        assert end.startswith("2025-12-31")

    def test_last_week_full_mon_sun(self):
        # 2026-04-20 is Monday; last_week = 2026-04-13 (Mon) to 2026-04-19 (Sun)
        lbt = "2026-04-20 00:00:00"
        start, end = _expand_time_expression("last_week", lbt)
        assert start.startswith("2026-04-13")
        assert end.startswith("2026-04-19")

    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError):
            _expand_time_expression("next_century", _LBT)


# ── 4. Empty-result diagnosis ──────────────────────────────────────────────────

class TestEmptyResultDiagnosis:
    def _make_executor(self, *, device_count=0, region_count=0) -> ToolExecutorService:
        repo = MagicMock()
        repo.device_record_count_async = AsyncMock(return_value=device_count)
        repo.region_record_count_async = AsyncMock(return_value=region_count)
        rule_repo = MagicMock()
        rule_repo.get_active_rule_profile = AsyncMock(return_value=_profile())
        svc = ToolExecutorService(repository=repo, rule_repository=rule_repo)
        svc._rule_profile_loaded = True
        return svc

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

    def test_status_label_not_in_results_warns(self):
        qt = {"status_counts": {"normal": 5}}
        result = self._SVC.verify(
            answer_type="soil_detail_answer",
            answer_bundle=self._bundle("该设备当前为重旱状态，含水量低。"),
            query_result=qt,
            tool_trace=[{"result": qt}],
            answer_facts={"record_count": 5},
            resolved_args={},
        )
        assert result["failed"] is False
        assert any("状态核验" in w for w in result["warnings"])

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

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.rule_repository import SoilRuleProfile
from app.services.agent_service import SoilAgentService
from app.services.parameter_resolver_service import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    ParameterResolverService,
)
from app.services.tool_executor_service import ToolExecutorService


_LBT = "2026-04-20 12:00:00"
_WINDOW = {
    "start_time": "2026-04-14 00:00:00",
    "end_time": "2026-04-20 23:59:59",
}


def _alias_row(
    alias_name: str,
    canonical_name: str,
    region_level: str,
    parent_city_name: str | None = None,
    alias_source: str = "generated_fact",
) -> dict[str, str | None]:
    return {
        "alias_name": alias_name,
        "canonical_name": canonical_name,
        "region_level": region_level,
        "parent_city_name": parent_city_name,
        "alias_source": alias_source,
    }


def _profile() -> SoilRuleProfile:
    return SoilRuleProfile(
        rule_name="soil_warning_v1",
        heavy_drought_max=50.0,
        waterlogging_min=150.0,
        device_fault_water20=0.0,
        device_fault_t20=0.0,
        rule_version="test@2026-01-01T00:00:00",
    )


class FakeAliasRepository:
    def __init__(self, *, versions: list[object], rows_by_version: dict[str, object]) -> None:
        self._versions = list(versions)
        self._rows_by_version = dict(rows_by_version)
        self._version_idx = 0
        self._current_version: str | None = None
        self.rows_calls = 0
        self.version_calls = 0

    async def region_alias_version_async(self) -> str:
        self.version_calls += 1
        item = self._versions[min(self._version_idx, len(self._versions) - 1)]
        self._version_idx += 1
        if isinstance(item, Exception):
            raise item
        self._current_version = str(item)
        return self._current_version

    async def region_alias_rows_async(self) -> list[dict[str, str | None]]:
        self.rows_calls += 1
        payload = self._rows_by_version[self._current_version or ""]
        if isinstance(payload, Exception):
            raise payload
        return list(payload)


class TestResolverLevelAwareNormalization:
    @pytest.mark.asyncio
    async def test_city_alias_auto_corrects_to_county(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("如东", "如东县", "county", "南通市"),
                    _alias_row("如东县", "如东县", "county", "南通市", alias_source="canonical"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"city": "如东", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is False
        assert result.entity_confidence == CONFIDENCE_MEDIUM
        assert "city" not in result.resolved_args
        assert result.resolved_args["county"] == "如东县"

    @pytest.mark.asyncio
    async def test_county_alias_auto_corrects_to_city(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("南通", "南通市", "city"),
                    _alias_row("南通市", "南通市", "city", alias_source="canonical"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"county": "南通", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is False
        assert result.entity_confidence == CONFIDENCE_MEDIUM
        assert "county" not in result.resolved_args
        assert result.resolved_args["city"] == "南通市"

    @pytest.mark.asyncio
    async def test_same_alias_name_keeps_city_and_county_candidates(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("海门", "海门市", "city"),
                    _alias_row("海门", "海门区", "county", "南通市"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        city_result = await svc.resolve(
            "query_soil_detail",
            {"city": "海门", **_WINDOW},
            _LBT,
        )
        county_result = await svc.resolve(
            "query_soil_detail",
            {"county": "海门", **_WINDOW},
            _LBT,
        )

        assert city_result.resolved_args["city"] == "海门市"
        assert county_result.resolved_args["county"] == "海门区"

    @pytest.mark.asyncio
    async def test_parent_city_mismatch_requires_clarification(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("南京市", "南京市", "city", alias_source="canonical"),
                    _alias_row("新北区", "新北区", "county", "常州市", alias_source="canonical"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"city": "南京市", "county": "新北区", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is True
        assert result.entity_confidence == CONFIDENCE_LOW

    @pytest.mark.asyncio
    async def test_single_edit_typo_normalizes_when_unique(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("苏州", "苏州市", "city"),
                    _alias_row("苏州市", "苏州市", "city", alias_source="canonical"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"city": "苏洲", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is False
        assert result.entity_confidence == CONFIDENCE_MEDIUM
        assert result.resolved_args["city"] == "苏州市"

    @pytest.mark.asyncio
    async def test_multi_candidate_alias_requires_clarification(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("新区", "浦口新区", "county", "南京市"),
                    _alias_row("新区", "滨海新区", "county", "天津市"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"county": "新区", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is True
        assert result.entity_confidence == CONFIDENCE_LOW

    @pytest.mark.asyncio
    async def test_unknown_suffixed_region_stays_low_confidence(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("南通市", "南通市", "city", alias_source="canonical"),
                    _alias_row("如东县", "如东县", "county", "南通市", alias_source="canonical"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_summary",
            {"city": "XX市", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is True
        assert result.entity_confidence == CONFIDENCE_LOW
        assert "city" not in result.resolved_args

    @pytest.mark.asyncio
    async def test_illegal_sn_is_blocked_as_low_confidence(self):
        repo = FakeAliasRepository(versions=["v1"], rows_by_version={"v1": []})
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"sn": "SNS001'; DROP TABLE soil_data; --", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is True
        assert result.entity_confidence == CONFIDENCE_LOW
        assert "sn" not in result.resolved_args


class TestAliasVersionedCache:
    @pytest.mark.asyncio
    async def test_alias_version_change_rebuilds_cache(self):
        repo = FakeAliasRepository(
            versions=["v1", "v2"],
            rows_by_version={
                "v1": [_alias_row("南通", "南通市", "city")],
                "v2": [_alias_row("海门", "海门区", "county", "南通市")],
            },
        )
        svc = ParameterResolverService(repository=repo)

        first = await svc.resolve(
            "query_soil_detail",
            {"city": "南通", **_WINDOW},
            _LBT,
        )
        second = await svc.resolve(
            "query_soil_detail",
            {"county": "海门", **_WINDOW},
            _LBT,
        )

        assert first.resolved_args["city"] == "南通市"
        assert second.resolved_args["county"] == "海门区"
        assert repo.rows_calls == 2

    @pytest.mark.asyncio
    async def test_alias_load_failure_reuses_previous_snapshot(self):
        repo = FakeAliasRepository(
            versions=["v1", "v2"],
            rows_by_version={
                "v1": [_alias_row("南通", "南通市", "city")],
                "v2": RuntimeError("reload failed"),
            },
        )
        svc = ParameterResolverService(repository=repo)

        first = await svc.resolve(
            "query_soil_detail",
            {"city": "南通", **_WINDOW},
            _LBT,
        )
        second = await svc.resolve(
            "query_soil_detail",
            {"city": "南通", **_WINDOW},
            _LBT,
        )

        assert first.resolved_args["city"] == "南通市"
        assert second.resolved_args["city"] == "南通市"
        assert repo.rows_calls == 2

    @pytest.mark.asyncio
    async def test_first_alias_load_failure_falls_back_to_empty_index(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={"v1": RuntimeError("initial load failed")},
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_detail",
            {"city": "如东", **_WINDOW},
            _LBT,
        )

        assert result.entity_confidence == CONFIDENCE_LOW
        assert result.should_clarify is True


class TestComparisonStructuredEntities:
    @pytest.mark.asyncio
    async def test_resolver_outputs_structured_region_entities(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("南通", "南通市", "city"),
                    _alias_row("如东", "如东县", "county", "南通市"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_comparison",
            {"entities": ["南通", "如东"], "entity_type": "region", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is False
        assert result.entity_confidence == CONFIDENCE_HIGH
        assert result.resolved_args["entities"] == [
            {
                "raw_name": "南通",
                "canonical_name": "南通市",
                "level": "city",
                "parent_city_name": None,
            },
            {
                "raw_name": "如东",
                "canonical_name": "如东县",
                "level": "county",
                "parent_city_name": "南通市",
            },
        ]

    @pytest.mark.asyncio
    async def test_resolver_clarifies_ambiguous_comparison_entities(self):
        repo = FakeAliasRepository(
            versions=["v1"],
            rows_by_version={
                "v1": [
                    _alias_row("新区", "浦口新区", "county", "南京市"),
                    _alias_row("新区", "滨海新区", "county", "天津市"),
                    _alias_row("如东", "如东县", "county", "南通市"),
                ]
            },
        )
        svc = ParameterResolverService(repository=repo)

        result = await svc.resolve(
            "query_soil_comparison",
            {"entities": ["新区", "如东"], "entity_type": "region", **_WINDOW},
            _LBT,
        )

        assert result.should_clarify is True
        assert result.entity_confidence == CONFIDENCE_LOW

    @pytest.mark.asyncio
    async def test_execute_comparison_branches_by_entity_level(self):
        calls: list[dict[str, object]] = []
        sample_record = {
            "sn": "SNS00204333",
            "city": "南通市",
            "county": "如东县",
            "create_time": "2026-04-13 23:59:17",
            "water20cm": 92.43,
        }

        async def _fake_filter_records_async(**kwargs):
            calls.append(kwargs)
            if kwargs.get("city") == "南通市" or kwargs.get("county") == "如东县":
                return [dict(sample_record)]
            return []

        repo = MagicMock()
        repo.filter_records_async = AsyncMock(side_effect=_fake_filter_records_async)
        repo.region_record_count_async = AsyncMock(return_value=1)
        repo.device_record_count_async = AsyncMock(return_value=1)
        rule_repo = MagicMock()
        rule_repo.get_active_rule_profile = AsyncMock(return_value=_profile())
        svc = ToolExecutorService(repository=repo, rule_repository=rule_repo)

        result = await svc.execute(
            tool_name="query_soil_comparison",
            tool_args={
                "entity_type": "region",
                "entities": [
                    {
                        "raw_name": "南通",
                        "canonical_name": "南通市",
                        "level": "city",
                        "parent_city_name": None,
                    },
                    {
                        "raw_name": "如东",
                        "canonical_name": "如东县",
                        "level": "county",
                        "parent_city_name": "南通市",
                    },
                ],
                "start_time": "2026-04-14 00:00:00",
                "end_time": "2026-04-20 23:59:59",
            },
        )

        assert result["total_entities"] == 2
        assert calls == [
            {
                "city": "南通市",
                "start_time": "2026-04-14 00:00:00",
                "end_time": "2026-04-20 23:59:59",
            },
            {
                "county": "如东县",
                "start_time": "2026-04-14 00:00:00",
                "end_time": "2026-04-20 23:59:59",
            },
        ]


class TestServiceWiring:
    def test_soil_agent_service_uses_repository_backed_resolver(self):
        repo = MagicMock()
        service = SoilAgentService(repository=repo)

        assert service.agent_loop_service.resolver._repository is repo

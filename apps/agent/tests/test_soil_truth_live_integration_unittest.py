"""Live-data truth verification for deterministic soil answers."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from app.repositories.soil_repository import SoilRepository
from app.services.data_answer_service import DataAnswerService


def _load_repo_root_env() -> None:
    """Load repo-root .env into process env when present for local integration tests."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


class SoilTruthLiveIntegrationTest(unittest.IsolatedAsyncioTestCase):
    """Verify live MySQL-backed soil answers against repository truth."""

    @classmethod
    def setUpClass(cls) -> None:
        _load_repo_root_env()
        required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise AssertionError(f"Live soil truth tests require MySQL env vars, missing: {', '.join(missing)}")

    async def asyncSetUp(self) -> None:
        self.repository = SoilRepository.from_env()
        self.service = DataAnswerService(repository=self.repository)

    async def test_live_summary_matches_repository_truth(self) -> None:
        result = await self.service.reply(
            message="最近7天全省整体墒情怎么样",
            session_id="soil-live-summary",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        log_entry = result["query_log_entries"][0]
        metrics = log_entry["executed_result_json"]["metrics"]
        records = self.repository.filter_records(
            start_time="2026-04-07 00:00:00",
            end_time="2026-04-13 23:59:59",
        )
        warning_records = self.repository.filter_warning_records(
            start_time="2026-04-07 00:00:00",
            end_time="2026-04-13 23:59:59",
        )
        device_keys = {
            str(record.get("sn") or "").strip()
            for record in records
            if str(record.get("sn") or "").strip()
        }
        region_keys = {
            (record.get("city"), record.get("county"))
            for record in records
            if record.get("city") or record.get("county")
        }

        self.assertEqual(log_entry["query_spec_json"]["dataset"], "fact_soil_moisture")
        self.assertIn("FROM fact_soil_moisture", log_entry["executed_sql_text"])
        self.assertNotIn("warning_disposal_record", log_entry["executed_sql_text"])
        self.assertEqual(metrics["record_count"], len(records))
        self.assertEqual(metrics["soil_record_count"], len(records))
        self.assertEqual(metrics["warning_record_count"], len(warning_records))
        self.assertEqual(metrics["device_count"], len(device_keys))
        self.assertEqual(metrics["region_count"], len(region_keys))

    async def test_live_warning_summary_matches_repository_truth_and_uses_soil_warning_source(self) -> None:
        result = await self.service.reply(
            message="最近30天有没有需要重点关注的地区",
            session_id="soil-live-warning-summary",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        log_entry = result["query_log_entries"][0]
        executed = log_entry["executed_result_json"]
        metrics = executed["metrics"]
        top_regions = executed["top_regions"]
        soil_records = self.repository.filter_records(
            start_time="2026-03-15 00:00:00",
            end_time="2026-04-13 23:59:59",
        )
        warning_records = self.repository.filter_warning_records(
            start_time="2026-03-15 00:00:00",
            end_time="2026-04-13 23:59:59",
        )
        preview_warning_total = sum(int(row.get("alert_record_count") or 0) for row in top_regions[:3])

        self.assertEqual(log_entry["query_spec_json"]["dataset"], "fact_soil_moisture")
        self.assertTrue(log_entry["query_spec_json"]["filters"].get("alert_only"))
        self.assertIn("FROM fact_soil_moisture", log_entry["executed_sql_text"])
        self.assertNotIn("warning_disposal_record", log_entry["executed_sql_text"])
        self.assertEqual(log_entry["row_count"], len(warning_records))
        self.assertEqual(metrics["record_count"], len(warning_records))
        self.assertEqual(metrics["soil_record_count"], len(soil_records))
        self.assertEqual(metrics["warning_record_count"], len(warning_records))
        self.assertIn("重点关注地区（前3个）：", result["final_text"])
        self.assertLess(preview_warning_total, metrics["warning_record_count"])

    async def test_live_warning_disposal_uses_disposal_source_only(self) -> None:
        result = await self.service.reply(
            message="最近30天全省预警处置情况怎么样",
            session_id="soil-live-warning-disposal",
            turn_id=1,
            current_context=None,
            timezone="Asia/Shanghai",
        )

        log_entry = result["query_log_entries"][0]
        stats = self.repository.query_warning_disposal_stats(
            start_time="2026-03-15 00:00:00",
            end_time="2026-04-13 23:59:59",
        )

        self.assertEqual(result["capability"], "warning_disposal")
        self.assertEqual(log_entry["query_spec_json"]["dataset"], "warning_disposal_record")
        self.assertIn("FROM warning_disposal_record", log_entry["executed_sql_text"])
        self.assertNotIn("fact_soil_moisture", log_entry["executed_sql_text"])
        self.assertEqual(log_entry["executed_result_json"], stats)


if __name__ == "__main__":
    unittest.main()

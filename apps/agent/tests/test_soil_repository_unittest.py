"""Unit tests for soil repository."""

import unittest
from unittest.mock import patch

from app.repositories.soil_repository import DatabaseUnavailableError, SoilRepository


class SoilRepositoryPathTest(unittest.TestCase):
    """Test cases for soil repository path."""
    def test_missing_mysql_config_raises_instead_of_seed_fallback(self):
        """Verify missing mysql config raises instead of seed fallback."""
        repository = SoilRepository()

        with self.assertRaises(DatabaseUnavailableError):
            repository.filter_records()

    def test_empty_mysql_result_returns_empty_list_instead_of_seed_fallback(self):
        """Verify empty mysql result returns empty list instead of seed fallback."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=EmptyResultConnection()):
            self.assertEqual(repository.filter_records(), [])

    def test_filter_records_returns_raw_fact_columns_only(self):
        """Verify query results do not append any derived warning/risk fields."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=RawRowConnection()):
            rows = repository.filter_records()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sn"], "SNS00000001")
        for banned_key in ("soil_status", "warning_level", "risk_score", "display_label", "rule_version"):
            self.assertNotIn(banned_key, rows[0])

    def test_missing_region_alias_table_returns_empty_alias_rows(self):
        """Verify missing region alias table returns empty alias rows."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=MissingRegionAliasConnection()):
            self.assertEqual(repository.region_alias_rows(), [])

    def test_filter_sql_escapes_date_format_percent_for_pyformat(self):
        """Verify filter sql escapes date format percent for pyformat."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        sql, params = repository._build_filter_records_query_pyformat(start_time="2026-04-01 00:00:00")

        rendered = sql % params
        self.assertIn("DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s')", rendered)

    def test_warning_rule_query_escapes_date_format_percent_for_pyformat(self):
        """Verify warning-rule query does not treat DATE_FORMAT markers as pyformat placeholders."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=RuleRowConnection()):
            row = repository.warning_rule_row()

        self.assertEqual(row["rule_code"], "soil_warning_v1")

    def test_warning_template_query_escapes_date_format_percent_for_pyformat(self):
        """Verify warning-template query does not treat DATE_FORMAT markers as pyformat placeholders."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        connection = TemplateRowConnection()
        with patch.object(repository, "_connect", return_value=connection):
            row = repository.warning_template_row()

        self.assertEqual(row["template_id"], "soil_default_warning")
        self.assertEqual(row["domain"], "soil_moisture")
        self.assertEqual(connection.last_cursor.params, ("soil_moisture",))

    def test_warning_record_query_escapes_date_format_percent_for_pyformat(self):
        """Verify warning-record query does not treat DATE_FORMAT markers as pyformat placeholders."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        connection = WarningRecordConnection()
        with patch.object(repository, "_connect", return_value=connection):
            rows = repository.query_warning_records(start_time="2026-04-01 00:00:00", end_time="2026-04-13 23:59:59")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["warning_level"], "heavy_drought")
        self.assertEqual(connection.last_cursor.params, ("2026-04-01 00:00:00", "2026-04-13 23:59:59", 50))

    def test_warning_disposal_audit_sql_uses_fixed_status_order_and_filters(self):
        """Verify warning disposal audit SQL keeps the fixed status mapping and literal filters."""
        sql = SoilRepository.build_warning_disposal_audit_sql(
            city="南通市",
            county="如东县",
            start_time="2026-04-01 00:00:00",
            end_time="2026-04-30 23:59:59",
        )

        self.assertIn("COUNT(*) AS total", sql)
        self.assertIn("SUM(pub_status = 3) AS status_done", sql)
        self.assertIn("SUM(pub_status = 1) AS status_pending", sql)
        self.assertIn("SUM(pub_status = 4) AS status_overtime_done", sql)
        self.assertIn("SUM(pub_status = 2) AS status_overtime_pending", sql)
        self.assertIn("city = '南通市'", sql)
        self.assertIn("county = '如东县'", sql)
        self.assertIn("warn_time >= '2026-04-01 00:00:00'", sql)
        self.assertIn("warn_time <= '2026-04-30 23:59:59'", sql)

    def test_warning_disposal_stats_maps_pub_status_counts(self):
        """Verify warning disposal stats map pub_status values to the fixed external labels."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        connection = WarningDisposalStatsConnection()
        with patch.object(repository, "_connect", return_value=connection):
            stats = repository.query_warning_disposal_stats(
                city="南通市",
                start_time="2026-04-01 00:00:00",
                end_time="2026-04-30 23:59:59",
            )

        self.assertEqual(
            stats,
            {
                "total": 10,
                "已处理": 6,
                "待处理": 2,
                "超时已处理": 1,
                "超时待处理": 1,
            },
        )
        self.assertEqual(
            connection.last_cursor.params,
            ("南通市", "2026-04-01 00:00:00", "2026-04-30 23:59:59"),
        )

    def test_warning_disposal_stats_returns_empty_when_table_missing(self):
        """Verify missing warning_disposal_record table returns an empty stats payload."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=MissingWarningDisposalConnection()):
            stats = repository.query_warning_disposal_stats()

        self.assertEqual(
            stats,
            {
                "total": 0,
                "已处理": 0,
                "待处理": 0,
                "超时已处理": 0,
                "超时待处理": 0,
            },
        )


class EmptyResultCursor:
    """Test double for empty result cursor."""
    def __enter__(self):
        """Handle enter on the empty result cursor."""
        return self

    def __exit__(self, exc_type, exc, traceback):
        """Handle exit on the empty result cursor."""
        return False

    def execute(self, sql, params):
        """Handle execute on the empty result cursor."""
        del sql, params

    def fetchall(self):
        """Handle fetchall on the empty result cursor."""
        return []


class EmptyResultConnection:
    """Test double for empty result connection."""
    def __init__(self):
        """Initialize the empty result connection."""
        self.closed = False

    def cursor(self):
        """Handle cursor on the empty result connection."""
        return EmptyResultCursor()

    def close(self):
        """Handle close on the empty result connection."""
        self.closed = True


class RawRowCursor:
    """Test double for one raw fact row."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params):
        del sql, params

    def fetchall(self):
        return [
            {
                "id": 1,
                "sn": "SNS00000001",
                "gatewayid": "gw-1",
                "sensorid": "sensor-1",
                "unitid": "unit-1",
                "city": "南通市",
                "county": "如东县",
                "time": "2026-04-30 00:00:00",
                "create_time": "2026-04-30 00:00:00",
                "water20cm": 41.2,
                "water40cm": 43.1,
                "water60cm": 44.5,
                "water80cm": 45.8,
                "t20cm": 18.2,
                "t40cm": 17.1,
                "t60cm": 16.6,
                "t80cm": 16.0,
                "water20cmfieldstate": 1,
                "water40cmfieldstate": 1,
                "water60cmfieldstate": 1,
                "water80cmfieldstate": 1,
                "t20cmfieldstate": 1,
                "t40cmfieldstate": 1,
                "t60cmfieldstate": 1,
                "t80cmfieldstate": 1,
                "lat": 32.31,
                "lon": 121.19,
            }
        ]


class RawRowConnection:
    """Connection wrapper for one raw fact query."""

    def __init__(self):
        self.closed = False

    def cursor(self):
        return RawRowCursor()

    def close(self):
        self.closed = True


class MissingRegionAliasCursor:
    """Test double for missing region alias cursor."""
    def __enter__(self):
        """Handle enter on the missing region alias cursor."""
        return self

    def __exit__(self, exc_type, exc, traceback):
        """Handle exit on the missing region alias cursor."""
        return False

    def execute(self, sql, params=None):
        """Handle execute on the missing region alias cursor."""
        del sql, params
        raise Exception("(1146, \"Table 'smart_agriculture.region_alias' doesn't exist\")")

    def fetchall(self):
        """Handle fetchall on the missing region alias cursor."""
        return []


class MissingRegionAliasConnection:
    """Test double for missing region alias connection."""
    def __init__(self):
        """Initialize the missing region alias connection."""
        self.closed = False

    def cursor(self):
        """Handle cursor on the missing region alias connection."""
        return MissingRegionAliasCursor()

    def close(self):
        """Handle close on the missing region alias connection."""
        self.closed = True


class RuleRowCursor:
    """Test double that mimics one warning-rule lookup."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        rendered = sql % params
        self.rendered = rendered

    def fetchone(self):
        return {
            "rule_code": "soil_warning_v1",
            "rule_name": "土壤墒情预警规则",
            "rule_scope": "soil",
            "rule_definition_json": "{}",
            "enabled": 1,
            "updated_at": "2026-04-30 00:00:00",
        }


class RuleRowConnection:
    """Connection wrapper for warning-rule lookup tests."""

    def cursor(self):
        return RuleRowCursor()

    def close(self):
        return None


class TemplateRowCursor:
    """Test double that mimics one warning-template lookup."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        rendered = sql % params
        self.rendered = rendered

    def fetchone(self):
        return {
            "template_id": "soil_default_warning",
            "domain": "soil_moisture",
            "warning_type": "soil_moisture",
            "audience": "farmer",
            "template_name": "土壤墒情预警模板",
            "template_text": "模板内容",
            "required_fields_json": "[]",
            "version": "v1",
            "enabled": 1,
            "created_at": "2026-04-30 00:00:00",
            "updated_at": "2026-04-30 00:00:00",
        }


class TemplateRowConnection:
    """Connection wrapper for warning-template lookup tests."""

    def __init__(self):
        self.last_cursor = None

    def cursor(self):
        self.last_cursor = TemplateRowCursor()
        return self.last_cursor

    def close(self):
        return None


class WarningRecordCursor:
    """Test double that mimics one warning-record lookup."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        rendered = sql % params
        self.rendered = rendered

    def fetchall(self):
        return [
            {
                "sn": "SNS00000001",
                "city": "南通市",
                "county": "如东县",
                "create_time": "2026-04-13 23:59:17",
                "water20cm": 42.1,
                "water40cm": 45.0,
                "warning_level": "heavy_drought",
            }
        ]


class WarningRecordConnection:
    """Connection wrapper for warning-record lookup tests."""

    def __init__(self):
        self.last_cursor: WarningRecordCursor | None = None

    def cursor(self):
        self.last_cursor = WarningRecordCursor()
        return self.last_cursor

    def close(self):
        return None


class WarningDisposalStatsCursor:
    """Test double that mimics one warning-disposal stats lookup."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {
            "total": 10,
            "status_done": 6,
            "status_pending": 2,
            "status_overtime_done": 1,
            "status_overtime_pending": 1,
        }


class WarningDisposalStatsConnection:
    """Connection wrapper for warning-disposal stats lookup tests."""

    def __init__(self):
        self.last_cursor: WarningDisposalStatsCursor | None = None

    def cursor(self):
        self.last_cursor = WarningDisposalStatsCursor()
        return self.last_cursor

    def close(self):
        return None


class MissingWarningDisposalCursor:
    """Test double for a missing warning_disposal_record table."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        del sql, params
        raise Exception("(1146, \"Table 'smart_agriculture.warning_disposal_record' doesn't exist\")")

    def fetchone(self):
        return None


class MissingWarningDisposalConnection:
    """Connection wrapper for missing warning_disposal_record table tests."""

    def cursor(self):
        return MissingWarningDisposalCursor()

    def close(self):
        return None


if __name__ == "__main__":
    unittest.main()

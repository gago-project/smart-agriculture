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

    def test_missing_region_alias_table_returns_empty_alias_rows(self):
        """Verify missing region alias table returns empty alias rows."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=MissingRegionAliasConnection()):
            self.assertEqual(repository.region_alias_rows(), [])

    def test_filter_sql_escapes_date_format_percent_for_pyformat(self):
        """Verify filter sql escapes date format percent for pyformat."""
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        sql, params = repository._build_filter_records_query_pyformat(batch_id="batch-1")

        rendered = sql % params
        self.assertIn("DATE_FORMAT(sample_time, '%Y-%m-%d %H:%i:%s')", rendered)


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


if __name__ == "__main__":
    unittest.main()

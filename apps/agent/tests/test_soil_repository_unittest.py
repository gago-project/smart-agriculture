import unittest
from unittest.mock import patch

from app.repositories.soil_repository import DatabaseUnavailableError, SoilRepository


class SoilRepositoryPathTest(unittest.TestCase):
    def test_missing_mysql_config_raises_instead_of_seed_fallback(self):
        repository = SoilRepository()

        with self.assertRaises(DatabaseUnavailableError):
            repository.filter_records()

    def test_empty_mysql_result_returns_empty_list_instead_of_seed_fallback(self):
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=EmptyResultConnection()):
            self.assertEqual(repository.filter_records(), [])

    def test_missing_region_alias_table_returns_empty_alias_rows(self):
        repository = SoilRepository(mysql_host="127.0.0.1", mysql_database="smart_agriculture", mysql_user="root", mysql_password="secret")

        with patch.object(repository, "_connect", return_value=MissingRegionAliasConnection()):
            self.assertEqual(repository.region_alias_rows(), [])


class EmptyResultCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params):
        del sql, params

    def fetchall(self):
        return []


class EmptyResultConnection:
    def __init__(self):
        self.closed = False

    def cursor(self):
        return EmptyResultCursor()

    def close(self):
        self.closed = True


class MissingRegionAliasCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        del sql, params
        raise Exception("(1146, \"Table 'smart_agriculture.region_alias' doesn't exist\")")

    def fetchall(self):
        return []


class MissingRegionAliasConnection:
    def __init__(self):
        self.closed = False

    def cursor(self):
        return MissingRegionAliasCursor()

    def close(self):
        self.closed = True


if __name__ == "__main__":
    unittest.main()

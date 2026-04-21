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


if __name__ == "__main__":
    unittest.main()

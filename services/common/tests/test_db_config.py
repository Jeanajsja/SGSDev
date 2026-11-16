import os
import unittest
from unittest.mock import patch

import psycopg2

from common.db_config import get_connection


class TestDatabaseConnection(unittest.TestCase):
    def test_missing_credentials_are_reported(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DB_HOST, DB_USER, DB_PASSWORD"):
                get_connection()

    def test_connection_failure_is_not_returned_as_empty_connection(self):
        environment = {
            "DB_HOST": "db.example.supabase.co",
            "DB_PORT": "5432",
            "DB_USER": "postgres",
            "DB_PASSWORD": "test-password",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch(
                "common.db_config.psycopg2.connect",
                side_effect=psycopg2.OperationalError("database unavailable"),
            ):
                with self.assertRaisesRegex(ConnectionError, "No se pudo conectar"):
                    get_connection()


if __name__ == "__main__":
    unittest.main()

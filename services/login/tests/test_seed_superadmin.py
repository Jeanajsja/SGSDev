import os
import unittest
from unittest.mock import patch

from seed_superadmin import asegurar_superadmin
from werkzeug.security import check_password_hash


class FakeCursor:
    def __init__(self):
        self.query = None
        self.parameters = None

    def execute(self, query, parameters):
        self.query = query
        self.parameters = parameters


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class TestSuperadminBootstrap(unittest.TestCase):
    def test_existing_account_is_not_reset_during_startup(self):
        connection = FakeConnection()
        with patch.dict(os.environ, {"SUPERADMIN_PASSWORD": "secure-test-password"}):
            result = asegurar_superadmin(lambda: connection)

        self.assertTrue(result)
        self.assertIn("INSERT INTO usuario", connection.cursor_instance.query)
        self.assertIn("ON CONFLICT DO NOTHING", connection.cursor_instance.query)
        self.assertNotIn("UPDATE usuario", connection.cursor_instance.query)
        self.assertTrue(
            check_password_hash(connection.cursor_instance.parameters[2], "secure-test-password")
        )
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

    def test_empty_bootstrap_password_does_not_connect(self):
        with patch.dict(os.environ, {"SUPERADMIN_PASSWORD": ""}):
            self.assertFalse(asegurar_superadmin(lambda: self.fail("unexpected connection")))


if __name__ == "__main__":
    unittest.main()

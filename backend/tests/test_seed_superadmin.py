import os
import unittest
from unittest.mock import patch

from seed_superadmin import asegurar_superadmin
from werkzeug.security import check_password_hash


class FakeCursor:
    def __init__(self, existing=None):
        self.existing = existing
        self.queries = []
        self.parameters = None
        self._last_query = ""

    def execute(self, query, parameters=None):
        self.queries.append(query)
        self.parameters = parameters
        self._last_query = query

    def fetchone(self):
        if "SELECT" in self._last_query.upper():
            return self.existing
        return None


class FakeConnection:
    def __init__(self, existing=None):
        self.cursor_instance = FakeCursor(existing=existing)
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class TestSuperadminBootstrap(unittest.TestCase):
    def test_crea_cuenta_si_no_existe(self):
        connection = FakeConnection(existing=None)
        with patch.dict(os.environ, {"SUPERADMIN_PASSWORD": "secure-test-password"}):
            result = asegurar_superadmin(lambda: connection)

        self.assertTrue(result)
        self.assertTrue(any("INSERT INTO usuario" in q for q in connection.cursor_instance.queries))
        self.assertTrue(
            check_password_hash(connection.cursor_instance.parameters[2], "secure-test-password")
        )
        self.assertTrue(connection.committed)

    def test_no_resetea_si_ya_existe(self):
        connection = FakeConnection(existing={"id_usuario": 1})
        with patch.dict(os.environ, {"SUPERADMIN_PASSWORD": "secure-test-password"}):
            result = asegurar_superadmin(lambda: connection)

        self.assertFalse(result)
        self.assertFalse(any("INSERT INTO usuario" in q for q in connection.cursor_instance.queries))
        self.assertFalse(connection.committed)

    def test_sin_password_no_conecta(self):
        with patch.dict(os.environ, {"SUPERADMIN_PASSWORD": ""}):
            self.assertFalse(asegurar_superadmin(lambda: self.fail("unexpected connection")))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import MagicMock

from seed_salones import LABS, SALONES, asegurar_salones_base


class FakeCursor:
    def __init__(self):
        self.existing = set()
        self.inserted = []
        self._last = ""

    def execute(self, query, params=None):
        q = " ".join(query.split()).lower()
        self._last = q
        if q.startswith("select"):
            self._params = params
            return
        if q.startswith("insert"):
            self.inserted.append(params[0])
            self.existing.add(params[0].lower())

    def fetchone(self):
        if self._last.startswith("select"):
            nombre = (self._params or [""])[0].lower()
            return (1,) if nombre in self.existing else None
        return None


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


class TestSeedSalones(unittest.TestCase):
    def test_crea_salon1_a_10_y_lab1_a_10(self):
        conn = FakeConnection()
        creados = asegurar_salones_base(lambda: conn)
        self.assertEqual(creados, 20)
        self.assertEqual(set(conn.cursor_instance.inserted), set(SALONES + LABS))
        self.assertTrue(conn.committed)

    def test_no_duplica_si_ya_existen(self):
        conn = FakeConnection()
        asegurar_salones_base(lambda: conn)
        conn2 = FakeConnection()
        conn2.cursor_instance.existing = {n.lower() for n in SALONES + LABS}
        creados = asegurar_salones_base(lambda: conn2)
        self.assertEqual(creados, 0)
        self.assertEqual(conn2.cursor_instance.inserted, [])


if __name__ == "__main__":
    unittest.main()

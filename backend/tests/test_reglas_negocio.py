import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from repositories.memory_salon_repository import MemorySalonRepository
from services.salon_service import CAPACIDAD_MAXIMA, CAPACIDAD_MINIMA, SalonService


class TestCapacidadSalon(unittest.TestCase):
    def setUp(self):
        self.service = SalonService(MemorySalonRepository())

    def test_capacidad_minima_1(self):
        res = self.service.crear({"nombre": "S1", "capacidad": CAPACIDAD_MINIMA, "ubicacion": "A"})
        self.assertEqual(res["status"], "ok")

    def test_capacidad_maxima_20(self):
        res = self.service.crear({"nombre": "S2", "capacidad": CAPACIDAD_MAXIMA, "ubicacion": "A"})
        self.assertEqual(res["status"], "ok")

    def test_rechaza_menos_de_1(self):
        res = self.service.crear({"nombre": "S3", "capacidad": 0, "ubicacion": "A"})
        self.assertEqual(res["status"], "error")
        self.assertIn("mínima", res["message"])

    def test_rechaza_mas_de_20(self):
        res = self.service.crear({"nombre": "S4", "capacidad": 21, "ubicacion": "A"})
        self.assertEqual(res["status"], "error")
        self.assertIn("máxima", res["message"])


if __name__ == "__main__":
    unittest.main()

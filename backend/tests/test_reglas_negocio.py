import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from repositories.memory_reserva_repository import MemoryReservaRepository
from repositories.memory_salon_repository import MemorySalonRepository
from services.reserva_service import ReservaService
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


class TestSalonesDisponibles(unittest.TestCase):
    def test_solo_aparecen_disponibles(self):
        repo = MemorySalonRepository()
        service = SalonService(repo)
        service.crear({"nombre": "Libre", "capacidad": 10, "ubicacion": "A"})
        service.crear({"nombre": "Ocupado", "capacidad": 10, "ubicacion": "B"})
        repo._salones[1]["estado"] = "ocupado"
        disponibles = service.listar_disponibles()
        self.assertEqual(len(disponibles), 1)
        self.assertEqual(disponibles[0]["nombre"], "Libre")


class TestCancelacionReserva(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryReservaRepository()
        self.service = ReservaService(self.repo)
        futuro = datetime.now() + timedelta(days=2)
        self.fecha = futuro.strftime("%Y-%m-%d")
        self.hora = "10:00"
        self.service.crear_reserva(
            {
                "fecha": self.fecha,
                "hora_inicio": self.hora,
                "hora_fin": "12:00",
                "id_salon": 1,
                "id_docente": 1,
            }
        )
        self.id_reserva = self.repo._reservas[0]["id_reserva"]

    def test_cancelada_desaparece_de_la_lista(self):
        self.assertEqual(self.service.cancelar_reserva(self.id_reserva)["status"], "ok")
        ids = [r["id_reserva"] for r in self.service.listar()["data"]]
        self.assertNotIn(self.id_reserva, ids)


if __name__ == "__main__":
    unittest.main()

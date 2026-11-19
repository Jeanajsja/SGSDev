import unittest

from reserva_service import ReservaService


class FakeReservaRepository:
    def __init__(self):
        self.reservas = [
            {"id_reserva": 10, "id_docente": 7, "id_salon": 2},
            {"id_reserva": 11, "id_docente": 8, "id_salon": 3},
        ]
        self.cancelled = []
        self.cruce_salon = False
        self.cruce_docente = False
        self.created = []

    def existe_cruce(self, id_salon, fecha, hora_inicio, hora_fin, excluir_id=None):
        return self.cruce_salon

    def existe_cruce_docente(self, id_docente, fecha, hora_inicio, hora_fin, excluir_id=None):
        return self.cruce_docente

    def crear(self, fecha, hora_inicio, hora_fin, id_docente, id_salon):
        self.created.append(
            {
                "fecha": fecha,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "id_docente": id_docente,
                "id_salon": id_salon,
            }
        )

    def listar_detalle(self):
        return self.reservas

    def cancelar(self, id_reserva):
        self.cancelled.append(id_reserva)
        return 2

    def promover_siguiente_cola(self, id_salon):
        pass

    def encolar(self, id_salon, id_docente):
        raise AssertionError("ya no se debe encolar ante traslape")

    def actualizar(self, id_reserva, fecha, hora_inicio, hora_fin, id_salon, id_docente):
        return True


class TestReservaServiceAuthorization(unittest.TestCase):
    def setUp(self):
        self.repository = FakeReservaRepository()
        self.service = ReservaService(self.repository)

    def test_docente_only_receives_own_reservations(self):
        result = self.service.listar({"id_usuario": 7, "id_rol": 3})
        self.assertEqual([row["id_reserva"] for row in result["data"]], [10])

    def test_docente_cannot_cancel_another_users_reservation(self):
        result = self.service.cancelar_reserva(11, {"id_usuario": 7, "id_rol": 3})
        self.assertEqual(result["status"], "error")
        self.assertEqual(self.repository.cancelled, [])

    def test_docente_can_cancel_own_reservation(self):
        result = self.service.cancelar_reserva(10, {"id_usuario": 7, "id_rol": 3})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(self.repository.cancelled, [10])

    def test_database_error_checking_availability_does_not_create_reservation(self):
        class UnavailableRepository(FakeReservaRepository):
            def existe_cruce(self, id_salon, fecha, hora_inicio, hora_fin, excluir_id=None):
                raise ConnectionError("database unavailable")

            def crear(self, fecha, hora_inicio, hora_fin, id_docente, id_salon):
                raise AssertionError("cannot reserve without checking availability")

        service = ReservaService(UnavailableRepository())
        result = service.crear_reserva(
            {
                "fecha": "2026-12-01",
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "id_docente": 7,
                "id_salon": 2,
            }
        )

        self.assertEqual(result["status"], "error")

    def test_rechaza_traslape_de_salon(self):
        self.repository.cruce_salon = True
        result = self.service.crear_reserva(
            {
                "fecha": "2026-12-01",
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "id_docente": 7,
                "id_salon": 2,
            }
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("traslaparse", result["message"].lower())
        self.assertEqual(self.repository.created, [])

    def test_rechaza_traslape_de_docente(self):
        self.repository.cruce_docente = True
        result = self.service.crear_reserva(
            {
                "fecha": "2026-12-01",
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "id_docente": 7,
                "id_salon": 2,
            }
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("docente", result["message"].lower())
        self.assertEqual(self.repository.created, [])


if __name__ == "__main__":
    unittest.main()

import unittest

import psycopg2
from repositories.postgres_reserva_repository import PostgresReservaRepository
from reserva_service import ReservaService


class FailingCursor:
    def execute(self, query, parameters):
        raise psycopg2.OperationalError("database query failed")


class FailingConnection:
    def __init__(self):
        self.closed = False

    def cursor(self, cursor_factory=None):
        return FailingCursor()

    def close(self):
        self.closed = True


class FakeReservaRepository:
    def __init__(self):
        self.reservas = [
            {"id_reserva": 10, "id_docente": 7, "id_salon": 2},
            {"id_reserva": 11, "id_docente": 8, "id_salon": 3},
        ]
        self.cancelled = []

    def existe_cruce(self, id_salon, fecha, hora_inicio, hora_fin):
        return False

    def crear(self, fecha, hora_inicio, hora_fin, id_docente, id_salon):
        pass

    def listar_detalle(self):
        return self.reservas

    def cancelar(self, id_reserva):
        self.cancelled.append(id_reserva)
        return 2

    def promover_siguiente_cola(self, id_salon):
        pass


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

    def test_availability_database_error_does_not_create_reservation(self):
        class UnavailableRepository(FakeReservaRepository):
            def existe_cruce(self, id_salon, fecha, hora_inicio, hora_fin):
                raise ConnectionError("database unavailable")

            def crear(self, fecha, hora_inicio, hora_fin, id_docente, id_salon):
                raise AssertionError(
                    "reservation must not be written when availability is unknown"
                )

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


class TestPostgresReservaRepository(unittest.TestCase):
    def test_availability_query_error_is_not_treated_as_no_conflict(self):
        connection = FailingConnection()
        repository = PostgresReservaRepository(lambda: connection)

        with self.assertRaisesRegex(ConnectionError, "comprobar la disponibilidad"):
            repository.existe_cruce(2, "2026-12-01", "09:00", "10:00")

        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()

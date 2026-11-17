import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from interfaces.email_validator import IEmailValidator
from interfaces.password_hasher import IPasswordHasher
from interfaces.password_verifier import IPasswordVerifier
from repositories.memory_reserva_repository import MemoryReservaRepository
from repositories.memory_salon_repository import MemorySalonRepository
from repositories.memory_usuario_repository import MemoryUsuarioRepository
from services.email_validator import validar_dominio_email
from services.login_service import LoginService
from services.password_policy import validar_password
from services.reserva_service import ReservaService
from services.salon_service import CAPACIDAD_MAXIMA, CAPACIDAD_MINIMA, SalonService
from services.usuario_service import UsuarioService


class FakeHasher(IPasswordHasher):
    def hash(self, password: str) -> str:
        return f"hash:{password}"


class FakeVerifier(IPasswordVerifier):
    def verificar(self, password: str, almacenado: str) -> bool:
        return almacenado == f"hash:{password}" or almacenado == password


class FakeEmailOk(IEmailValidator):
    def validar(self, email):
        return None


CLAVE = "Clave1234"
ANCLA = "lfpaez30@ucatolica.edu.co"


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
        ahora = datetime.strptime(f"{self.fecha} 01:00:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(self.service.cancelar_reserva(self.id_reserva, ahora=ahora)["status"], "ok")
        ids = [r["id_reserva"] for r in self.service.listar()["data"]]
        self.assertNotIn(self.id_reserva, ids)

    def test_no_cancela_con_menos_de_8_horas(self):
        inicio = datetime.strptime(f"{self.fecha} {self.hora}:00", "%Y-%m-%d %H:%M:%S")
        ahora = inicio - timedelta(hours=7)
        res = self.service.cancelar_reserva(self.id_reserva, ahora=ahora)
        self.assertEqual(res["status"], "error")
        self.assertIn("8 horas", res["message"])

    def test_cancela_con_8_horas_o_mas(self):
        inicio = datetime.strptime(f"{self.fecha} {self.hora}:00", "%Y-%m-%d %H:%M:%S")
        ahora = inicio - timedelta(hours=8)
        self.assertEqual(self.service.cancelar_reserva(self.id_reserva, ahora=ahora)["status"], "ok")


class TestCargaDocente(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryReservaRepository()
        self.service = ReservaService(self.repo)

    def test_maximo_10_horas_al_dia(self):
        fecha = "2026-09-14"
        self.service.crear_reserva(
            {"fecha": fecha, "hora_inicio": "07:00", "hora_fin": "12:00", "id_salon": 1, "id_docente": 2}
        )
        self.service.crear_reserva(
            {"fecha": fecha, "hora_inicio": "12:00", "hora_fin": "17:00", "id_salon": 2, "id_docente": 2}
        )
        exceso = self.service.crear_reserva(
            {"fecha": fecha, "hora_inicio": "17:00", "hora_fin": "18:00", "id_salon": 3, "id_docente": 2}
        )
        self.assertEqual(exceso["status"], "error")
        self.assertIn("10 horas", exceso["message"])

    def test_maximo_46_horas_semanales(self):
        # lunes a viernes: 5 dias x 9h = 45h; el sexto bloque de 2h rompe el tope
        dias = ["2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18"]
        for i, fecha in enumerate(dias):
            self.service.crear_reserva(
                {
                    "fecha": fecha,
                    "hora_inicio": "07:00",
                    "hora_fin": "16:00",
                    "id_salon": i + 1,
                    "id_docente": 5,
                }
            )
        exceso = self.service.crear_reserva(
            {
                "fecha": "2026-09-19",
                "hora_inicio": "08:00",
                "hora_fin": "10:00",
                "id_salon": 10,
                "id_docente": 5,
            }
        )
        self.assertEqual(exceso["status"], "error")
        self.assertIn("46 horas", exceso["message"])


class TestPasswordYRegistro(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryUsuarioRepository()
        self.service = UsuarioService(self.repo, FakeHasher(), FakeEmailOk())
        self.repo.crear("Luisa", ANCLA, f"hash:{CLAVE}", 1, "activo")

    def test_password_minimo_8_letras_y_numeros(self):
        self.assertIsNotNone(validar_password("abc123"))
        self.assertIsNotNone(validar_password("abcdefgh"))
        self.assertIsNotNone(validar_password("12345678"))
        self.assertIsNone(validar_password(CLAVE))

    def test_restablecer_password(self):
        res = self.service.restablecer_password(ANCLA, "Nueva4567")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(self.repo.buscar_por_email(ANCLA)["password"], "hash:Nueva4567")
        malo = self.service.restablecer_password(ANCLA, "corta1")
        self.assertEqual(malo["status"], "error")

    def test_validacion_correo(self):
        self.assertEqual(validar_dominio_email("ana@gmal.com")["status"], "error")
        self.assertIsNone(validar_dominio_email("ana@gmail.com"))

    def test_un_registro_por_correo(self):
        primero = self.service.crear_usuario(
            {
                "nombre": "Ana",
                "email": "ana@gmail.com",
                "password": CLAVE,
                "id_rol": 3,
                "solicitante_email": ANCLA,
            }
        )
        self.assertEqual(primero["status"], "ok")
        segundo = self.service.crear_usuario(
            {"nombre": "Otra", "email": "ana@gmail.com", "password": CLAVE, "id_rol": 2}
        )
        self.assertEqual(segundo["status"], "error")
        self.assertIn("un registro por correo", segundo["message"])

    
if __name__ == "__main__":
    unittest.main()

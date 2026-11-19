import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

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


class TestTraslapeHorario(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryReservaRepository()
        self.service = ReservaService(self.repo)
        self.service.crear_reserva(
            {
                "fecha": "2026-09-14",
                "hora_inicio": "08:00",
                "hora_fin": "10:00",
                "id_salon": 1,
                "id_docente": 2,
            }
        )

    def test_rechaza_mismo_salon_misma_hora(self):
        choque = self.service.crear_reserva(
            {
                "fecha": "2026-09-14",
                "hora_inicio": "09:00",
                "hora_fin": "11:00",
                "id_salon": 1,
                "id_docente": 3,
            }
        )
        self.assertEqual(choque["status"], "error")
        self.assertIn("ocupado", choque["message"].lower())
        self.assertEqual(len(self.repo._reservas), 1)

    def test_rechaza_mismo_docente_otra_sala_misma_hora(self):
        choque = self.service.crear_reserva(
            {
                "fecha": "2026-09-14",
                "hora_inicio": "09:00",
                "hora_fin": "11:00",
                "id_salon": 2,
                "id_docente": 2,
            }
        )
        self.assertEqual(choque["status"], "error")
        self.assertIn("docente", choque["message"].lower())
        self.assertEqual(len(self.repo._reservas), 1)

    def test_permite_mismo_horario_otro_salon_otro_docente(self):
        ok = self.service.crear_reserva(
            {
                "fecha": "2026-09-14",
                "hora_inicio": "08:00",
                "hora_fin": "10:00",
                "id_salon": 2,
                "id_docente": 3,
            }
        )
        self.assertEqual(ok["status"], "ok", ok)


class TestCargaDocente(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryReservaRepository()
        self.service = ReservaService(self.repo)

    def test_clase_no_puede_durar_mas_de_2_horas(self):
        exceso = self.service.crear_reserva(
            {"fecha": "2026-09-14", "hora_inicio": "08:00", "hora_fin": "11:00", "id_salon": 1, "id_docente": 2}
        )
        self.assertEqual(exceso["status"], "error")
        self.assertIn("no puede durar más de 2 horas", exceso["message"])
        self.assertIn("No es posible realizar la reserva", exceso["message"])

    def test_maximo_8_horas_diarias(self):
        # 4 clases de 2h = 8h; una quinta debe fallar
        for i, (ini, fin) in enumerate(
            [("07:00", "09:00"), ("09:00", "11:00"), ("11:00", "13:00"), ("13:00", "15:00")]
        ):
            creado = self.service.crear_reserva(
                {
                    "fecha": "2026-09-14",
                    "hora_inicio": ini,
                    "hora_fin": fin,
                    "id_salon": i + 1,
                    "id_docente": 2,
                }
            )
            self.assertEqual(creado["status"], "ok", creado)
        exceso = self.service.crear_reserva(
            {"fecha": "2026-09-14", "hora_inicio": "15:00", "hora_fin": "17:00", "id_salon": 5, "id_docente": 2}
        )
        self.assertEqual(exceso["status"], "error")
        self.assertIn("8 horas", exceso["message"])

    def test_maximo_46_horas_semanales(self):
        # 23 clases de 2h = 46h repartidas en la semana; una más rompe el tope
        bloques = [("07:00", "09:00"), ("09:00", "11:00"), ("11:00", "13:00"), ("13:00", "15:00")]
        salon = 1
        creadas = 0
        for dia in range(14, 20):  # lun-sab
            for ini, fin in bloques:
                if creadas >= 23:
                    break
                res = self.service.crear_reserva(
                    {
                        "fecha": f"2026-09-{dia}",
                        "hora_inicio": ini,
                        "hora_fin": fin,
                        "id_salon": salon,
                        "id_docente": 5,
                    }
                )
                self.assertEqual(res["status"], "ok", res)
                creadas += 1
                salon += 1
            if creadas >= 23:
                break
        exceso = self.service.crear_reserva(
            {
                "fecha": "2026-09-19",
                "hora_inicio": "15:00",
                "hora_fin": "17:00",
                "id_salon": 100,
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
        from services.reset_pin_store import generar_pin, guardar_pin

        with patch.dict(
            "os.environ",
            {"JWT_SECRET": "sgsdev-local-jwt-secret-change-in-prod-32chars"},
            clear=False,
        ):
            pin = generar_pin()
            guardar_pin(ANCLA, pin)
            res = self.service.restablecer_password(
                email=ANCLA, pin=pin, nueva_password="Nueva4567"
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(self.repo.buscar_por_email(ANCLA)["password"], "hash:Nueva4567")
            malo = self.service.restablecer_password(
                email=ANCLA, pin="000000", nueva_password="corta1"
            )
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

    def test_rol_queda_en_espera_sin_superadmin(self):
        res = self.service.crear_usuario(
            {"nombre": "Pedro", "email": "pedro@gmail.com", "password": CLAVE, "id_rol": 3}
        )
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["estado"], "pendiente")
        usuario = self.repo.buscar_por_email("pedro@gmail.com")
        self.assertEqual(usuario["estado"], "pendiente")

        login = LoginService(self.repo, FakeVerifier())
        bloqueado = login.login("pedro@gmail.com", CLAVE)
        self.assertEqual(bloqueado["status"], "error")
        self.assertIn("espera", bloqueado["message"])

        self.service.cambiar_rol(usuario["id_usuario"], 3, ANCLA)
        self.assertEqual(self.repo.buscar_por_id(usuario["id_usuario"])["estado"], "activo")
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret-" * 4}):
            self.assertEqual(login.login("pedro@gmail.com", CLAVE)["status"], "ok")


if __name__ == "__main__":
    unittest.main()

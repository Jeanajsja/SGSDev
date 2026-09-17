import unittest
from repositories.memory_salon_repository import MemorySalonRepository
from repositories.memory_usuario_repository import MemoryUsuarioRepository
from services.email_validator import validar_dominio_email
from services.salon_service import SalonService
from services.usuario_service import UsuarioService
from interfaces.password_hasher import IPasswordHasher


class FakeHasher(IPasswordHasher):
    """LSP: hasher de prueba que sustituye a Werkzeug."""

    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verificar(self, password: str, almacenado: str) -> bool:
        return almacenado == f"hash:{password}" or almacenado == password


class TestEmailValidator(unittest.TestCase):
    def test_typo_gmail(self):
        res = validar_dominio_email("ana@gmal.com")
        self.assertEqual(res["status"], "error")
        self.assertIn("gmail.com", res["message"])

    def test_dominio_valido(self):
        self.assertIsNone(validar_dominio_email("ana@gmail.com"))


class TestSalonService(unittest.TestCase):
    def setUp(self):
        self.service = SalonService(MemorySalonRepository())

    def test_crear_y_listar(self):
        res = self.service.crear({"nombre": "Lab Redes", "capacidad": 30, "ubicacion": "Piso 3"})
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(self.service.listar()), 1)

    def test_capacidad_invalida(self):
        res = self.service.crear({"nombre": "Lab", "capacidad": 0, "ubicacion": "Piso 1"})
        self.assertEqual(res["status"], "error")


class TestUsuarioService(unittest.TestCase):
    def setUp(self):
        self.service = UsuarioService(MemoryUsuarioRepository(), FakeHasher())

    def test_login_ok(self):
        self.service.crear_usuario(
            {"nombre": "Ana", "email": "ana@gmail.com", "password": "123", "id_rol": 1}
        )
        res = self.service.login("ana@gmail.com", "123")
        self.assertEqual(res["status"], "ok")
        self.assertNotIn("password", res["user"])

    def test_email_invalido_no_toca_repositorio(self):
        res = self.service.crear_usuario(
            {"nombre": "Ana", "email": "ana@gmal.com", "password": "123", "id_rol": 1}
        )
        self.assertEqual(res["status"], "error")
        self.assertIsNone(self.service.login("ana@gmal.com", "123").get("user"))


if __name__ == "__main__":
    unittest.main()

import unittest

from interfaces.password_verifier import IPasswordVerifier
from login_service import LoginService
from repositories.memory_login_repository import MemoryLoginRepository


class FakeVerifier(IPasswordVerifier):
    def verificar(self, password: str, almacenado: str) -> bool:
        return almacenado == password or almacenado == f"hash:{password}"


class TestLoginService(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryLoginRepository()
        self.repo.agregar(
            {
                "id_usuario": 1,
                "nombre": "Ana",
                "email": "ana@gmail.com",
                "password": "hash:123",
                "id_rol": 1,
                "estado": "activo",
            }
        )
        self.service = LoginService(self.repo, FakeVerifier())

    def test_login_ok(self):
        res = self.service.login("ana@gmail.com", "123")
        self.assertEqual(res["status"], "ok")
        self.assertNotIn("password", res["user"])

    def test_login_malo(self):
        res = self.service.login("ana@gmail.com", "otra")
        self.assertEqual(res["status"], "error")

    def test_isp_verifier_sin_hash(self):
        self.assertTrue(hasattr(IPasswordVerifier, "verificar"))
        self.assertFalse(hasattr(IPasswordVerifier, "hash"))


if __name__ == "__main__":
    unittest.main()

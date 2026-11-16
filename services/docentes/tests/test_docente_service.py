import unittest

from docente_service import DocenteService


class FakeRepository:
    def __init__(self):
        self.created = None

    def crear(self, nombre, correo, password_hash):
        self.created = (nombre, correo, password_hash)

    def listar(self):
        return []


class FakePasswordHasher:
    def __init__(self):
        self.password = None

    def hash(self, password):
        self.password = password
        return f"hashed:{password}"


class FakeEmailValidator:
    def validar(self, email):
        return None


class TestDocenteService(unittest.TestCase):
    def test_creation_uses_provided_password_without_returning_it(self):
        repository = FakeRepository()
        hasher = FakePasswordHasher()
        service = DocenteService(repository, hasher, FakeEmailValidator())

        result = service.crear(
            {
                "nombre": "Docente",
                "correo": "docente@ucatolica.edu.co",
                "password": "una-clave-segura-123",
            }
        )

        self.assertEqual(hasher.password, "una-clave-segura-123")
        self.assertEqual(repository.created[2], "hashed:una-clave-segura-123")
        self.assertNotIn("password", result)


if __name__ == "__main__":
    unittest.main()

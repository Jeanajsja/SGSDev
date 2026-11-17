import unittest

from usuario_service import UsuarioService


SUPERADMIN_ANCLA = "lfpaez30@ucatolica.edu.co"


class FakeRepository:
    def __init__(self):
        self.created = []

    def buscar_por_email(self, email):
        if email.lower() == SUPERADMIN_ANCLA:
            return {"email": SUPERADMIN_ANCLA, "id_rol": 1}
        return None

    def crear(self, nombre, email, password_hash, id_rol, estado="activo"):
        self.created.append((nombre, email, password_hash, id_rol, estado))

    def listar(self):
        return []

    def buscar_por_id(self, id_usuario):
        return None

    def actualizar_rol(self, id_usuario, id_rol):
        return False

    def actualizar_password(self, email, password_hash):
        return False

    def eliminar(self, id_usuario):
        return False


class FakePasswordHasher:
    def hash(self, password):
        return f"hashed:{password}"


class FakeEmailValidator:
    def validar(self, email):
        return None


class TestUsuarioServiceAuthorization(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.service = UsuarioService(
            self.repository,
            FakePasswordHasher(),
            FakeEmailValidator(),
        )

    def test_only_anchor_can_create_superadmin(self):
        data = {
            "nombre": "Nuevo administrador",
            "email": "nuevo@ucatolica.edu.co",
            "password": "una-clave-segura-123",
            "id_rol": 1,
        }

        denied = self.service.crear_usuario(data, "admin@ucatolica.edu.co")
        allowed = self.service.crear_usuario(data, SUPERADMIN_ANCLA)

        self.assertEqual(denied["status"], "error")
        self.assertEqual(allowed["status"], "ok")
        self.assertEqual(self.repository.created[0][3], 1)


if __name__ == "__main__":
    unittest.main()

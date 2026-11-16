import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from common.auth import crear_token_acceso
from usuario_controller import crear_router


class FakeUsuarioService:
    def __init__(self):
        self.created = []

    def crear_usuario(self, data, solicitante_email=None):
        self.created.append((data, solicitante_email))
        return {"status": "ok", "message": "creada"}

    def listar_usuarios(self):
        return {"status": "ok", "data": []}

    def cambiar_rol(self, id_usuario, id_rol, solicitante_email):
        return {"status": "ok", "message": "actualizado"}

    def eliminar_cuenta(self, id_usuario, solicitante_email):
        return {"status": "ok", "message": "eliminado"}


class TestUsuarioController(unittest.TestCase):
    def setUp(self):
        self.secret = "controller-test-secret-" * 3
        self.env = patch.dict(os.environ, {"JWT_SECRET": self.secret})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.service = FakeUsuarioService()
        app = FastAPI()
        app.include_router(crear_router(self.service))
        self.client = TestClient(app)

    def token(self, role, email="usuario@ucatolica.edu.co"):
        return crear_token_acceso(
            {"id_usuario": 7, "id_rol": role, "email": email}
        )

    def registro(self, role=3):
        return {
            "nombre": "Docente de Prueba",
            "email": "docente@ucatolica.edu.co",
            "password": "una-clave-segura-123",
            "id_rol": role,
        }

    def test_public_registration_can_only_create_docentes(self):
        denied = self.client.post("/api/usuarios", json=self.registro(role=2))
        allowed = self.client.post("/api/usuarios", json=self.registro())

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(self.service.created[0][1], None)

    def test_management_requires_superadmin_token(self):
        self.assertEqual(self.client.get("/api/usuarios").status_code, 401)
        admin_headers = {"Authorization": f"Bearer {self.token(2)}"}
        self.assertEqual(self.client.get("/api/usuarios", headers=admin_headers).status_code, 403)
        superadmin_headers = {"Authorization": f"Bearer {self.token(1)}"}
        self.assertEqual(self.client.get("/api/usuarios", headers=superadmin_headers).status_code, 200)

    def test_actor_email_comes_from_signed_token(self):
        headers = {"Authorization": f"Bearer {self.token(2, 'admin@ucatolica.edu.co')}"}
        response = self.client.post(
            "/api/usuarios",
            headers=headers,
            json={**self.registro(), "solicitante_email": "lfpaez30@ucatolica.edu.co"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.created[0][1], "admin@ucatolica.edu.co")
        denied = self.client.post(
            "/api/usuarios",
            headers=headers,
            json=self.registro(role=2),
        )
        self.assertEqual(denied.status_code, 403)

    def test_invalid_bearer_token_does_not_fall_back_to_public_registration(self):
        response = self.client.post(
            "/api/usuarios",
            headers={"Authorization": "Bearer invalid"},
            json=self.registro(),
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

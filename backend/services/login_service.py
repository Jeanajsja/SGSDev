import os
import sys

from interfaces.login_repository import ILoginRepository
from interfaces.password_verifier import IPasswordVerifier
from models.usuario_factory import usuario_desde_fila

_SERVICES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services"))
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

from common.auth import crear_token_acceso  # noqa: E402


class LoginService:
    def __init__(self, repository: ILoginRepository, password_verifier: IPasswordVerifier):
        self._repository = repository
        self._password_verifier = password_verifier

    def login(self, email, password):
        try:
            user = self._repository.buscar_por_email(email)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo conectar a la base de datos de Supabase"}
        except Exception as e:
            return {"status": "error", "message": f"Error en el servidor: {str(e)}"}

        if not user or not self._password_verifier.verificar(password, user["password"]):
            return {"status": "error", "message": "Credenciales inválidas"}

        estado = (user.get("estado") or "activo").lower()
        if estado == "pendiente":
            return {
                "status": "error",
                "message": "Tu cuenta está en espera de aprobación del superadministrador",
            }

        usuario_publico = usuario_desde_fila(user).to_public_dict()
        return {
            "status": "ok",
            "user": usuario_publico,
            "access_token": crear_token_acceso(usuario_publico),
            "token_type": "bearer",
        }

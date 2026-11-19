from interfaces.login_repository import ILoginRepository
from interfaces.password_verifier import IPasswordVerifier
from models.usuario import Usuario


class LoginService:
    def __init__(self, repository: ILoginRepository, password_verifier: IPasswordVerifier):
        self._repository = repository
        self._password_verifier = password_verifier

    def login(self, email, password):
        try:
            user = self._repository.buscar_por_email(email)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        except Exception:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}

        if not user or not self._password_verifier.verificar(password, user["password"]):
            return {"status": "error", "message": "Credenciales inválidas"}

        estado = (user.get("estado") or "activo").lower()
        if estado == "pendiente":
            return {
                "status": "error",
                "message": "Tu cuenta está en espera de aprobación del superadministrador",
            }

        return {"status": "ok", "user": Usuario.from_row(user).to_public_dict()}

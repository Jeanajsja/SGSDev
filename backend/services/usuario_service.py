from interfaces.password_hasher import IPasswordHasher
from interfaces.usuario_repository import IUsuarioRepository
from services.email_validator import validar_dominio_email


class UsuarioService:

    def __init__(self, repository: IUsuarioRepository, password_hasher: IPasswordHasher):
        self._repository = repository
        self._password_hasher = password_hasher

    def crear_usuario(self, data):
        error = validar_dominio_email(data.get("email", ""))
        if error:
            return error
        try:
            password_segura = self._password_hasher.hash(data["password"])
            self._repository.crear(data["nombre"], data["email"], password_segura, data["id_rol"])
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": f"El correo ya existe o hay un error: {str(e)}"}
        return {"status": "ok", "message": "Cuenta creada exitosamente"}

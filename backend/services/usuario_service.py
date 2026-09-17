from interfaces.email_validator import IEmailValidator
from interfaces.password_hasher import IPasswordHasher
from interfaces.usuario_repository import IUsuarioRepository


class UsuarioService:
    def __init__(self, repository: IUsuarioRepository, password_hasher: IPasswordHasher, email_validator: IEmailValidator):
        self._repository = repository
        self._password_hasher = password_hasher
        self._email_validator = email_validator

    def crear_usuario(self, data):
        error = self._email_validator.validar(data.get("email", ""))
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

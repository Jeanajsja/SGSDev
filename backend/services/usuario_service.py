from interfaces.password_hasher import IPasswordHasher
from interfaces.usuario_repository import IUsuarioRepository
from services.email_validator import validar_dominio_email


class UsuarioService:
    """SRP: registro y login. DIP: repositorio + hasher inyectados."""

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

    def login(self, email, password):
        try:
            user = self._repository.buscar_por_email(email)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo conectar a la base de datos de Supabase"}
        except Exception as e:
            return {"status": "error", "message": f"Error en el servidor: {str(e)}"}

        if user and self._password_hasher.verificar(password, user["password"]):
            user_clean = dict(user)
            user_clean.pop("password", None)
            return {"status": "ok", "user": user_clean}
        return {"status": "error", "message": "Credenciales inválidas"}

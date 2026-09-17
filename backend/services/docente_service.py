from interfaces.docente_repository import IDocenteRepository
from interfaces.password_hasher import IPasswordHasher
from models.docente import Docente
from services.email_validator import validar_dominio_email


class DocenteService:
    def __init__(self, repository: IDocenteRepository, password_hasher: IPasswordHasher):
        self._repository = repository
        self._password_hasher = password_hasher

    def listar(self):
        return [Docente.from_row(row).to_dict() for row in self._repository.listar()]

    def crear(self, data):
        error = validar_dominio_email(data.get("correo", ""))
        if error:
            return error
        try:
            password_defecto = self._password_hasher.hash("docente123")
            self._repository.crear(data["nombre"], data["correo"], password_defecto)
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": f"Error al registrar docente: {str(e)}"}
        return {"status": "ok", "message": "Docente registrado con éxito. Contraseña por defecto: docente123"}

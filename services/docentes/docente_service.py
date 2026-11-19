from common.ttl_cache import TtlCache
from interfaces.docente_repository import IDocenteRepository
from interfaces.email_validator import IEmailValidator
from interfaces.password_hasher import IPasswordHasher
from models.docente import Docente

_cache = TtlCache(ttl_sec=30)


class DocenteService:
    def __init__(self, repository: IDocenteRepository, password_hasher: IPasswordHasher, email_validator: IEmailValidator):
        self._repository = repository
        self._password_hasher = password_hasher
        self._email_validator = email_validator

    def listar(self):
        cached = _cache.get("docentes")
        if cached is not None:
            return cached
        data = [Docente.from_row(row).to_dict() for row in self._repository.listar()]
        _cache.set("docentes", data)
        return data

    def crear(self, data):
        error = self._email_validator.validar(data.get("correo", ""))
        if error:
            return error
        try:
            password_segura = self._password_hasher.hash(data["password"])
            self._repository.crear(data["nombre"], data["correo"], password_segura)
            _cache.invalidate("docentes")
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": f"Error al registrar docente: {str(e)}"}
        return {"status": "ok", "message": "Docente registrado con éxito"}

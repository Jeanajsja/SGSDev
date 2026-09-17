from interfaces.rol_repository import IRolRepository
from models.rol import Rol


class RolService:
    def __init__(self, repository: IRolRepository):
        self._repository = repository

    def listar(self):
        return [Rol.from_row(row).to_dict() for row in self._repository.listar()]

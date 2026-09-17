from interfaces.rol_repository import IRolRepository


class RolService:
    def __init__(self, repository: IRolRepository):
        self._repository = repository

    def listar(self):
        return self._repository.listar()

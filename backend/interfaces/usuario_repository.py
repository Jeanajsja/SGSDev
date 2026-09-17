from abc import ABC, abstractmethod


class IUsuarioRepository(ABC):
    @abstractmethod
    def crear(self, nombre, email, password_hash, id_rol):
        pass

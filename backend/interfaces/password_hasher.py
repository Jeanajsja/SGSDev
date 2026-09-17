from abc import ABC, abstractmethod


class IPasswordHasher(ABC):

    @abstractmethod
    def hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verificar(self, password: str, almacenado: str) -> bool:
        pass

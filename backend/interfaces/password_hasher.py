from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """ISP + DIP: el servicio no depende de Werkzeug, solo de este contrato."""

    @abstractmethod
    def hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verificar(self, password: str, almacenado: str) -> bool:
        pass

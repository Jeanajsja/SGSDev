from abc import ABC, abstractmethod


class ISalonRepository(ABC):
    """ISP: solo operaciones de salones."""

    @abstractmethod
    def listar(self):
        pass

    @abstractmethod
    def crear(self, nombre, capacidad, ubicacion):
        pass

    @abstractmethod
    def actualizar(self, id_salon, nombre, capacidad, ubicacion):
        pass

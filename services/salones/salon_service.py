from common.ttl_cache import TtlCache
from interfaces.salon_repository import ISalonRepository
from models.salon import Salon

CAPACIDAD_MINIMA = 1
CAPACIDAD_MAXIMA = 20
_cache = TtlCache(ttl_sec=30)


class SalonService:
    def __init__(self, repository: ISalonRepository):
        self._repository = repository

    def listar(self):
        cached = _cache.get("salones")
        if cached is not None:
            return cached
        data = [Salon.from_row(row).to_dict() for row in self._repository.listar()]
        _cache.set("salones", data)
        return data

    def listar_disponibles(self):
        return [
            salon
            for salon in self.listar()
            if (salon.get("estado") or "").lower() == "disponible"
        ]

    def crear(self, data):
        error = self._validar(data)
        if error:
            return error
        try:
            self._repository.crear(data["nombre"].strip(), int(data["capacidad"]), data["ubicacion"].strip())
            _cache.invalidate("salones")
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        return {"status": "ok", "message": "Salón registrado exitosamente"}

    def actualizar(self, id_salon, data):
        error = self._validar(data)
        if error:
            return error
        try:
            filas = self._repository.actualizar(
                id_salon,
                data["nombre"].strip(),
                int(data["capacidad"]),
                data["ubicacion"].strip(),
            )
            _cache.invalidate("salones")
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        if filas > 0:
            return {"status": "ok", "message": "Salón actualizado correctamente"}
        return {"status": "error", "message": "No se encontró el salón para actualizar"}

    def _validar(self, data):
        if not data:
            return {"status": "error", "message": "Datos de salón requeridos"}
        nombre = (data.get("nombre") or "").strip()
        ubicacion = (data.get("ubicacion") or "").strip()
        if not nombre:
            return {"status": "error", "message": "El nombre del salón es obligatorio"}
        if not ubicacion:
            return {"status": "error", "message": "La ubicación del salón es obligatoria"}
        try:
            capacidad = int(data.get("capacidad"))
        except (TypeError, ValueError):
            return {"status": "error", "message": "La capacidad debe ser un número entero"}
        if capacidad < CAPACIDAD_MINIMA:
            return {
                "status": "error",
                "message": f"La capacidad mínima es {CAPACIDAD_MINIMA} estudiante",
            }
        if capacidad > CAPACIDAD_MAXIMA:
            return {
                "status": "error",
                "message": f"La capacidad máxima es {CAPACIDAD_MAXIMA} estudiantes",
            }
        return None

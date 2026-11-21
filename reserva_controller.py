from typing import Optional
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from reserva_service import ReservaService


class ReservaPayload(BaseModel):
    fecha: str
    hora_inicio: str
    hora_fin: Optional[str] = None
    id_salon: int
    id_clase: Optional[int] = None
    id_docente: Optional[int] = None

    def as_reserva_data(self) -> dict:
        data = self.model_dump()
        id_clase = data.get("id_clase") if data.get("id_clase") is not None else data.get("id_docente")
        if id_clase is None:
            raise ValueError("Se requiere el ID clase de la reserva")
        data["id_clase"] = id_clase
        data["id_docente"] = id_clase
        return data


def crear_router(service: ReservaService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["reservas"])

    @router.get("/reservas")
    def listar():
        res = service.listar()
        if res.get("status") != "ok":
            return JSONResponse(content={"status": "error", "message": res.get("message")}, status_code=500)
        return {"status": "ok", "data": jsonable_encoder(res.get("data"))}

    @router.get("/reservas/salones-disponibles")
    def salones_disponibles(
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_id: Optional[int] = None,
    ):
        res = service.listar_salones_disponibles(
            fecha, hora_inicio, hora_fin, excluir_id=excluir_id
        )
        if res.get("status") != "ok":
            return JSONResponse(content=res, status_code=400)
        return {"status": "ok", "data": jsonable_encoder(res.get("data"))}

    @router.post("/reservas")
    def crear(payload: ReservaPayload):
        try:
            return service.crear_reserva(payload.as_reserva_data())
        except ValueError as e:
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=422)

    @router.put("/reservas/{id_reserva}")
    def actualizar(id_reserva: int, payload: ReservaPayload):
        try:
            return service.actualizar_reserva(id_reserva, payload.as_reserva_data())
        except ValueError as e:
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=422)

    @router.delete("/reservas/{id_reserva}")
    def cancelar(id_reserva: int):
        return service.cancelar_reserva(id_reserva)

    return router

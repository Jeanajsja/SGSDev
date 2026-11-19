from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from common.auth import requiere_rol, usuario_actual
from reserva_service import ReservaService


class ReservaPayload(BaseModel):
    fecha: str
    hora_inicio: str
    hora_fin: Optional[str] = None
    id_salon: int = Field(gt=0)
    id_clase: Optional[int] = Field(default=None, gt=0)
    id_docente: Optional[int] = Field(default=None, gt=0)


def _resolver_id_clase(data: dict, principal=None) -> dict:
    if principal and principal.get("id_rol") == 3:
        data["id_clase"] = principal["id_usuario"]
    elif data.get("id_clase") is None and data.get("id_docente") is not None:
        data["id_clase"] = data["id_docente"]
    if data.get("id_clase") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Se requiere el ID clase de la reserva",
        )
    data["id_docente"] = data["id_clase"]  # columna histórica en BD
    return data


def crear_router(service: ReservaService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["reservas"])

    @router.get("/reservas")
    def listar(principal=Depends(usuario_actual)):
        res = service.listar(principal)
        if res.get("status") != "ok":
            return JSONResponse(content={"status": "error", "message": res.get("message")}, status_code=500)
        return {"status": "ok", "data": jsonable_encoder(res.get("data"))}

    @router.get("/reservas/salones-disponibles")
    def salones_disponibles(
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        excluir_id: Optional[int] = None,
        _principal=Depends(usuario_actual),
    ):
        res = service.listar_salones_disponibles(
            fecha, hora_inicio, hora_fin, excluir_id=excluir_id
        )
        if res.get("status") != "ok":
            return JSONResponse(content=res, status_code=400)
        return {"status": "ok", "data": jsonable_encoder(res.get("data"))}

    @router.post("/reservas")
    def crear(payload: ReservaPayload, principal=Depends(usuario_actual)):
        data = _resolver_id_clase(payload.model_dump(), principal)
        return service.crear_reserva(data)

    @router.put("/reservas/{id_reserva}")
    def actualizar(
        id_reserva: int,
        payload: ReservaPayload,
        _principal=Depends(requiere_rol(1, 2)),
    ):
        data = _resolver_id_clase(payload.model_dump())
        return service.actualizar_reserva(id_reserva, data)

    @router.delete("/reservas/{id_reserva}")
    def cancelar(id_reserva: int, principal=Depends(usuario_actual)):
        return service.cancelar_reserva(id_reserva, principal)

    return router

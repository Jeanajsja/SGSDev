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
    id_docente: Optional[int] = Field(default=None, gt=0)


def crear_router(service: ReservaService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["reservas"])

    @router.get("/reservas")
    def listar(principal=Depends(usuario_actual)):
        res = service.listar(principal)
        if res.get("status") != "ok":
            return JSONResponse(content={"status": "error", "message": res.get("message")}, status_code=500)
        return {"status": "ok", "data": jsonable_encoder(res.get("data"))}

    @router.post("/reservas")
    def crear(payload: ReservaPayload, principal=Depends(usuario_actual)):
        data = payload.model_dump()
        if principal["id_rol"] == 3:
            data["id_docente"] = principal["id_usuario"]
        elif data["id_docente"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Se requiere el docente asociado a la reserva",
            )
        return service.crear_reserva(data)

    @router.put("/reservas/{id_reserva}")
    def actualizar(
        id_reserva: int,
        payload: ReservaPayload,
        _principal=Depends(requiere_rol(1, 2)),
    ):
        if payload.id_docente is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Se requiere el docente asociado a la reserva",
            )
        return service.actualizar_reserva(id_reserva, payload.model_dump())

    @router.delete("/reservas/{id_reserva}")
    def cancelar(id_reserva: int, principal=Depends(usuario_actual)):
        return service.cancelar_reserva(id_reserva, principal)

    return router

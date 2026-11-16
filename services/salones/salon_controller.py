from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from common.auth import requiere_rol, usuario_actual
from salon_service import SalonService


class SalonPayload(BaseModel):
    nombre: str
    capacidad: int
    ubicacion: str


def crear_router(service: SalonService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["salones"])

    @router.get("/salones")
    def get_salones(_principal=Depends(usuario_actual)):
        return {"status": "ok", "data": jsonable_encoder(service.listar())}

    @router.post("/salones")
    def crear(payload: SalonPayload, _principal=Depends(requiere_rol(1))):
        return service.crear(payload.model_dump())

    @router.put("/salones/{id_salon}")
    def editar(id_salon: int, payload: SalonPayload, _principal=Depends(requiere_rol(1))):
        return service.actualizar(id_salon, payload.model_dump())

    return router

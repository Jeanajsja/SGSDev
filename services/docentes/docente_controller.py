from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from common.auth import requiere_rol
from docente_service import DocenteService


class DocenteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    correo: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=128)


def crear_router(service: DocenteService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["docentes"])

    @router.get("/docentes")
    def listar(_principal=Depends(requiere_rol(1, 2))):
        return {"status": "ok", "data": jsonable_encoder(service.listar())}

    @router.post("/docentes")
    def crear(payload: DocenteCreate, _principal=Depends(requiere_rol(1))):
        return service.crear(payload.model_dump())

    return router

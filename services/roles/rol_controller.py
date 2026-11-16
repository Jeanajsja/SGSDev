from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from common.auth import usuario_actual
from rol_service import RolService


def crear_router(service: RolService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["roles"])

    @router.get("/roles")
    def get_roles(_principal=Depends(usuario_actual)):
        return jsonable_encoder(service.listar())

    return router

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from usuario_service import UsuarioService


class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str
    id_rol: int


def crear_router(service: UsuarioService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["usuarios"])

    @router.post("/usuarios")
    def registrar(payload: UsuarioCreate):
        res = service.crear_usuario(payload.model_dump())
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    return router

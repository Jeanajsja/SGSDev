from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from common.auth import requiere_rol, usuario_opcional
from usuario_service import UsuarioService


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    id_rol: int = Field(default=3, ge=1, le=3)


class UsuarioRolUpdate(BaseModel):
    id_rol: int = Field(ge=1, le=3)


class OlvidePasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class RestablecerPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    nueva_password: str = Field(min_length=8, max_length=128)
    confirmar_password: str = Field(min_length=8, max_length=128)


def crear_router(service: UsuarioService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["usuarios"])

    @router.post("/usuarios/olvide-password")
    def olvide_password(payload: OlvidePasswordRequest):
        res = service.solicitar_restablecimiento(payload.email)
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    @router.post("/usuarios/restablecer-password")
    def restablecer_password(payload: RestablecerPasswordRequest):
        if payload.nueva_password != payload.confirmar_password:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "La confirmación de contraseña no coincide",
                },
                status_code=400,
            )
        res = service.restablecer_password(payload.token, payload.nueva_password)
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    @router.post("/usuarios")
    def registrar(payload: UsuarioCreate, principal=Depends(usuario_opcional)):
        if principal is None:
            if payload.id_rol != 3:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El registro público solo permite crear cuentas de docente",
                )
            solicitante_email = None
        else:
            if principal["id_rol"] not in {1, 2} or (
                principal["id_rol"] == 2 and payload.id_rol != 3
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para crear cuentas",
                )
            solicitante_email = principal["email"]

        res = service.crear_usuario(payload.model_dump(), solicitante_email)
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    @router.get("/usuarios")
    def listar(_principal=Depends(requiere_rol(1))):
        res = service.listar_usuarios()
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    @router.put("/usuarios/{id_usuario}")
    def cambiar_rol(
        id_usuario: int,
        payload: UsuarioRolUpdate,
        principal=Depends(requiere_rol(1)),
    ):
        res = service.cambiar_rol(id_usuario, payload.id_rol, principal["email"])
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    @router.delete("/usuarios/{id_usuario}")
    def eliminar(id_usuario: int, principal=Depends(requiere_rol(1))):
        res = service.eliminar_cuenta(id_usuario, principal["email"])
        if res and res.get("status") == "ok":
            return res
        return JSONResponse(content=res, status_code=400)

    return router

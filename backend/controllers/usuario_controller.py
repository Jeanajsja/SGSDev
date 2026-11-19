from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from dependencies import get_login_service, get_usuario_service
from schemas import (
    LoginRequest,
    OlvidePasswordRequest,
    RestablecerPasswordRequest,
    UsuarioCreate,
)
from services.login_service import LoginService
from services.usuario_service import UsuarioService

router = APIRouter(prefix="/api", tags=["usuarios"])


@router.post("/login")
def login(payload: LoginRequest, service: LoginService = Depends(get_login_service)):
    res = service.login(payload.email, payload.password)
    if res and res.get("status") == "ok":
        return jsonable_encoder(res)
    return JSONResponse(content=jsonable_encoder(res), status_code=401)


@router.post("/usuarios/olvide-password")
def olvide_password(
    payload: OlvidePasswordRequest,
    service: UsuarioService = Depends(get_usuario_service),
):
    res = service.solicitar_restablecimiento(payload.email)
    if res and res.get("status") == "ok":
        return res
    return JSONResponse(content=res, status_code=400)


@router.post("/usuarios/restablecer-password")
def restablecer_password(
    payload: RestablecerPasswordRequest,
    service: UsuarioService = Depends(get_usuario_service),
):
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
def registrar(payload: UsuarioCreate, service: UsuarioService = Depends(get_usuario_service)):
    res = service.crear_usuario(payload.model_dump())
    if res and res.get("status") == "ok":
        return res
    return JSONResponse(content=res, status_code=400)

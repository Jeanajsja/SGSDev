from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from schemas import LoginRequest, UsuarioCreate
from services.usuario_service import UsuarioService

router = APIRouter(prefix="/api", tags=["usuarios"])
service = UsuarioService()


@router.post("/login")
def login(payload: LoginRequest):
    res = service.login(payload.email, payload.password)
    if res and res.get("status") == "ok":
        return jsonable_encoder(res)
    return JSONResponse(content=jsonable_encoder(res), status_code=401)


@router.post("/usuarios")
def registrar(payload: UsuarioCreate):
    res = service.crear_usuario(payload.model_dump())
    if res and res.get("status") == "ok":
        return res
    return JSONResponse(content=res, status_code=400)

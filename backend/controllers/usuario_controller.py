from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from dependencies import get_usuario_service
from schemas import LoginRequest
from services.usuario_service import UsuarioService

router = APIRouter(prefix="/api", tags=["usuarios"])


@router.post("/login")
def login(payload: LoginRequest, service: UsuarioService = Depends(get_usuario_service)):
    res = service.login(payload.email, payload.password)
    if res and res.get("status") == "ok":
        return jsonable_encoder(res)
    return JSONResponse(content=jsonable_encoder(res), status_code=401)

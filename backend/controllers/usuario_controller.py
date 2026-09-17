from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from dependencies import get_usuario_service
from schemas import UsuarioCreate
from services.usuario_service import UsuarioService

router = APIRouter(prefix="/api", tags=["usuarios"])


@router.post("/usuarios")
def registrar(payload: UsuarioCreate, service: UsuarioService = Depends(get_usuario_service)):
    res = service.crear_usuario(payload.model_dump())
    if res and res.get("status") == "ok":
        return res
    return JSONResponse(content=res, status_code=400)

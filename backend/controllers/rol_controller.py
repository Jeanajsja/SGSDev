from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from services.rol_service import RolService

router = APIRouter(prefix="/api", tags=["roles"])
service = RolService()


@router.get("/roles")
def get_roles():
    return jsonable_encoder(service.listar())

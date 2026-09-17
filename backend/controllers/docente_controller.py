from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from schemas import DocenteCreate
from services.docente_service import DocenteService

router = APIRouter(prefix="/api", tags=["docentes"])
service = DocenteService()


@router.get("/docentes")
def listar():
    return {"status": "ok", "data": jsonable_encoder(service.listar())}


@router.post("/docentes")
def crear(payload: DocenteCreate):
    return service.crear(payload.model_dump())

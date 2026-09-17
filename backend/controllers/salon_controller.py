from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from schemas import SalonPayload
from services.salon_service import SalonService

router = APIRouter(prefix="/api", tags=["salones"])
service = SalonService()


@router.get("/salones")
def get_salones():
    return {"status": "ok", "data": jsonable_encoder(service.listar())}


@router.post("/salones")
def crear(payload: SalonPayload):
    return service.crear(payload.model_dump())


@router.put("/salones/{id_salon}")
def editar(id_salon: int, payload: SalonPayload):
    return service.actualizar(id_salon, payload.model_dump())

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db_config import get_connection
from repositories.postgres_salon_repository import PostgresSalonRepository
from salon_controller import crear_router
from salon_service import SalonService
from seed_salones import asegurar_salones_base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    try:
        creados = asegurar_salones_base(get_connection)
        if creados:
            logger.info("Salones y laboratorios base creados: %s", creados)
    except Exception:
        logger.exception("No se pudieron aprovisionar salones/laboratorios base")
    yield


def create_app(service=None):
    if service is None:
        service = SalonService(PostgresSalonRepository(get_connection))
    app = FastAPI(title="ms-salones", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "ms-salones"}

    app.include_router(crear_router(service))
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 5002)), reload=True)

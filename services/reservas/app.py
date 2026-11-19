import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db_config import get_connection, start_keepalive, warm_connection
from repositories.postgres_reserva_repository import PostgresReservaRepository
from reserva_controller import crear_router
from reserva_service import ReservaService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    try:
        warm_connection()
        start_keepalive()
    except Exception:
        logger.exception("No se pudo precalentar la conexión a Supabase")
    yield


def create_app(service=None):
    if service is None:
        service = ReservaService(PostgresReservaRepository(get_connection))
    app = FastAPI(title="ms-reservas", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "ms-reservas"}

    app.include_router(crear_router(service))
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 5006)), reload=True)

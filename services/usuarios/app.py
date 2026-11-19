import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db_config import get_connection, start_keepalive, warm_connection
from dominio_email_validator import DominioEmailValidator
from repositories.postgres_usuario_repository import PostgresUsuarioRepository
from security.werkzeug_password_hasher import WerkzeugPasswordHasher
from seed_superadmin import asegurar_superadmin
from usuario_controller import crear_router
from usuario_service import UsuarioService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    try:
        asegurar_superadmin(get_connection)
        warm_connection()
        start_keepalive()
    except Exception:
        logger.exception("No se pudo precalentar usuarios/Supabase")
    yield


def create_app(service=None):
    if service is None:
        service = UsuarioService(
            PostgresUsuarioRepository(get_connection),
            WerkzeugPasswordHasher(),
            DominioEmailValidator(),
        )
    app = FastAPI(title="ms-usuarios", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "ms-usuarios"}

    app.include_router(crear_router(service))
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 5005)), reload=True)

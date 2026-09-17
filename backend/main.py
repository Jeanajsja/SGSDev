import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.docente_controller import router as docente_router
from controllers.reserva_controller import router as reserva_router
from controllers.rol_controller import router as rol_router
from controllers.salon_controller import router as salon_router
from controllers.usuario_controller import router as usuario_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend/templates"))
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend/static"))


def create_app() -> FastAPI:
    """Composition root HTTP: ensambla routers. Las implementaciones se inyectan con Depends."""
    application = FastAPI(title="SGSDev", description="Sistema de Gestión de Salones")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(usuario_router)
    application.include_router(reserva_router)
    application.include_router(salon_router)
    application.include_router(docente_router)
    application.include_router(rol_router)

    templates = Jinja2Templates(directory=TEMPLATE_DIR)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", response_class=HTMLResponse)
    @application.get("/login.html", response_class=HTMLResponse)
    def login_page(request: Request):
        return templates.TemplateResponse("login.html", {"request": request})

    @application.get("/index.html", response_class=HTMLResponse)
    def index_page(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

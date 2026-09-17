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

app = FastAPI(title="SGSDev", description="Sistema de Gestión de Salones")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuario_router)
app.include_router(reserva_router)
app.include_router(salon_router)
app.include_router(docente_router)
app.include_router(rol_router)

templates = Jinja2Templates(directory=TEMPLATE_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
@app.get("/login.html", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/index.html", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

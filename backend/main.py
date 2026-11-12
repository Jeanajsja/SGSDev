from controllers.vista_controller import router as vista_router
from controllers.usuario_controller import router as usuario_router
from controllers.salon_controller import router as salon_router
from controllers.docente_controller import router as docente_router
from controllers.reserva_controller import router as reserva_router
from controllers.rol_controller import router as rol_router

def create_app() -> FastAPI:
    application = FastAPI(title="SGSDev", description="Sistema de Gestión de Salones")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(vista_router)
    application.include_router(usuario_router)
    application.include_router(salon_router)
    application.include_router(docente_router)
    application.include_router(reserva_router)
    application.include_router(rol_router)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return application

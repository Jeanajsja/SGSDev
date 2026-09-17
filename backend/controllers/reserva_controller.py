from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from database.db_config import get_connection
from psycopg2.extras import RealDictCursor
from schemas import ReservaPayload
from services.reserva_service import ReservaService

router = APIRouter(prefix="/api", tags=["reservas"])
service = ReservaService()


@router.get("/reservas")
def listar():
    conn = get_connection()
    if conn is None:
        return JSONResponse(
            content={"status": "error", "message": "No se pudo conectar a la base de datos"},
            status_code=500,
        )
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT r.id_reserva, r.fecha::TEXT, r.hora_inicio::TEXT, r.hora_fin::TEXT, r.estado,
                   COALESCE(u.nombre, 'Admin') as docente, s.nombre as salon, r.id_docente, r.id_salon
            FROM reserva r
            LEFT JOIN usuario u ON r.id_docente = u.id_usuario
            LEFT JOIN salon s ON r.id_salon = s.id_salon
            ORDER BY r.fecha DESC, r.hora_inicio DESC
        """
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        return {"status": "ok", "data": jsonable_encoder(data)}
    except Exception as e:
        if conn:
            conn.close()
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.post("/reservas")
def crear(payload: ReservaPayload):
    return service.crear_reserva(payload.model_dump())


@router.put("/reservas/{id_reserva}")
def actualizar(id_reserva: int, payload: ReservaPayload):
    return service.actualizar_reserva(id_reserva, payload.model_dump())


@router.delete("/reservas/{id_reserva}")
def cancelar(id_reserva: int):
    return service.cancelar_reserva(id_reserva)

import logging

logger = logging.getLogger(__name__)

CAPACIDAD_DEFAULT = 20
SALONES = [f"Salon{i}" for i in range(1, 11)]
LABS = [f"Lab{i}" for i in range(1, 11)]


UBICACION_DEFAULT = "Sede:CLS Edificio:O"


def _nombres_base():
    return [(nombre, UBICACION_DEFAULT) for nombre in SALONES] + [
        (nombre, UBICACION_DEFAULT) for nombre in LABS
    ]


def _existe(cursor, conn, nombre):
    for sql in (
        "SELECT 1 FROM salon WHERE lower(nombre) = lower(%s)",
        'SELECT 1 FROM "Salon" WHERE lower(nombre) = lower(%s)',
    ):
        try:
            cursor.execute(sql, (nombre,))
            return cursor.fetchone() is not None
        except Exception:
            conn.rollback()
    return False


def _insertar(cursor, conn, nombre, ubicacion):
    for sql in (
        """
        INSERT INTO salon (nombre, capacidad, estado, ubicacion)
        VALUES (%s, %s, %s, %s)
        """,
        """
        INSERT INTO "Salon" (nombre, capacidad, estado, ubicacion)
        VALUES (%s, %s, %s, %s)
        """,
    ):
        try:
            cursor.execute(sql, (nombre, CAPACIDAD_DEFAULT, "disponible", ubicacion))
            return True
        except Exception:
            conn.rollback()
    return False


def asegurar_salones_base(connection_factory):
    """Crea Salon1..Salon10 y Lab1..Lab10 si aún no existen (por nombre)."""
    conn = connection_factory()
    if conn is None:
        raise ConnectionError("No se pudo conectar para aprovisionar salones")
    try:
        cursor = conn.cursor()
        creados = 0
        for nombre, ubicacion in _nombres_base():
            if _existe(cursor, conn, nombre):
                continue
            if _insertar(cursor, conn, nombre, ubicacion):
                creados += 1
        conn.commit()
        if creados:
            logger.info("Salones/labs base creados: %s", creados)
        return creados
    finally:
        conn.close()

import logging
import re

logger = logging.getLogger(__name__)

CAPACIDAD_DEFAULT = 20
SALONES = [f"Sala{i}" for i in range(1, 11)]
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


def _renombrar_salon_a_sala(cursor, conn):
    """Migra nombres históricos SalonN -> SalaN sin romper unicidad."""
    for sql_listar in (
        "SELECT id_salon, nombre FROM salon WHERE nombre ~* '^salon[0-9]+$'",
        'SELECT id_salon, nombre FROM "Salon" WHERE nombre ~* \'^salon[0-9]+$\'',
    ):
        try:
            cursor.execute(sql_listar)
            filas = cursor.fetchall() or []
        except Exception:
            conn.rollback()
            continue

        renombrados = 0
        for fila in filas:
            if isinstance(fila, dict):
                id_salon = fila.get("id_salon")
                nombre = fila.get("nombre")
            else:
                id_salon, nombre = fila[0], fila[1]
            match = re.match(r"(?i)^salon(\d+)$", str(nombre or ""))
            if not match:
                continue
            nuevo = f"Sala{match.group(1)}"
            if _existe(cursor, conn, nuevo):
                for sql_del in (
                    """
                    DELETE FROM salon s
                    WHERE s.id_salon = %s
                      AND NOT EXISTS (
                          SELECT 1 FROM reserva r WHERE r.id_salon = s.id_salon
                      )
                    """,
                    """
                    DELETE FROM "Salon" s
                    WHERE s.id_salon = %s
                      AND NOT EXISTS (
                          SELECT 1 FROM reserva r WHERE r.id_salon = s.id_salon
                      )
                    """,
                ):
                    try:
                        cursor.execute(sql_del, (id_salon,))
                        break
                    except Exception:
                        conn.rollback()
                continue
            for sql_upd in (
                "UPDATE salon SET nombre = %s WHERE id_salon = %s",
                'UPDATE "Salon" SET nombre = %s WHERE id_salon = %s',
            ):
                try:
                    cursor.execute(sql_upd, (nuevo, id_salon))
                    if cursor.rowcount:
                        renombrados += 1
                    break
                except Exception:
                    conn.rollback()
        return renombrados
    return 0


def asegurar_salones_base(connection_factory):
    """Crea Sala1..Sala10 y Lab1..Lab10 si aún no existen (por nombre)."""
    conn = connection_factory()
    if conn is None:
        raise ConnectionError("No se pudo conectar para aprovisionar salones")
    try:
        cursor = conn.cursor()
        renombrados = _renombrar_salon_a_sala(cursor, conn)
        creados = 0
        for nombre, ubicacion in _nombres_base():
            if _existe(cursor, conn, nombre):
                continue
            if _insertar(cursor, conn, nombre, ubicacion):
                creados += 1
        conn.commit()
        if renombrados:
            logger.info("Salones renombrados a SalaN: %s", renombrados)
        if creados:
            logger.info("Salas/labs base creados: %s", creados)
        return creados + renombrados
    finally:
        conn.close()

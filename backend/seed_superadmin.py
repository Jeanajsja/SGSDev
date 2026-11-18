import logging
import os

from werkzeug.security import generate_password_hash

from superadmin_ancla import ROL_SUPERADMIN, SUPERADMIN_ANCLA, SUPERADMIN_NOMBRE

logger = logging.getLogger(__name__)


def asegurar_superadmin(connection_factory, password=None):
    """Crea la cuenta ancla solo si no existe. No modifica contraseñas existentes."""
    password = password if password is not None else os.getenv("SUPERADMIN_PASSWORD", "")
    if not password:
        return False
    if len(password) < 12:
        raise ValueError("SUPERADMIN_PASSWORD debe tener al menos 12 caracteres")

    conn = connection_factory()
    if conn is None:
        raise ConnectionError("No se pudo conectar para aprovisionar el superadministrador")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_usuario FROM usuario WHERE lower(email) = lower(%s)",
            (SUPERADMIN_ANCLA,),
        )
        if cursor.fetchone():
            return False

        password_hash = generate_password_hash(password)
        try:
            cursor.execute(
                """
                INSERT INTO usuario (nombre, email, password, id_rol, estado)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (SUPERADMIN_NOMBRE, SUPERADMIN_ANCLA, password_hash, ROL_SUPERADMIN, "activo"),
            )
        except Exception:
            conn.rollback()
            cursor.execute(
                """
                INSERT INTO usuario (nombre, email, password, id_rol)
                VALUES (%s, %s, %s, %s)
                """,
                (SUPERADMIN_NOMBRE, SUPERADMIN_ANCLA, password_hash, ROL_SUPERADMIN),
            )
        conn.commit()
        logger.info("Cuenta ancla aprovisionada: %s", SUPERADMIN_ANCLA)
        return True
    finally:
        conn.close()

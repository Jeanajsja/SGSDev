import os

from werkzeug.security import generate_password_hash
from superadmin_ancla import ROL_SUPERADMIN, SUPERADMIN_ANCLA, SUPERADMIN_NOMBRE


def asegurar_superadmin(connection_factory, password=None):
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
            """
            INSERT INTO usuario (nombre, email, password, id_rol)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                SUPERADMIN_NOMBRE,
                SUPERADMIN_ANCLA,
                generate_password_hash(password),
                ROL_SUPERADMIN,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return True

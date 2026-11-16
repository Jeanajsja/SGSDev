import os

from werkzeug.security import generate_password_hash

from db_config import get_connection
from superadmin_ancla import SUPERADMIN_ANCLA


def restablecer_contrasena_superadmin():
    password = os.getenv("SUPERADMIN_PASSWORD", "")
    if len(password) < 12:
        raise ValueError("SUPERADMIN_PASSWORD debe tener al menos 12 caracteres")

    conn = get_connection()
    if conn is None:
        raise ConnectionError("No se pudo conectar para actualizar la contraseña")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE usuario
            SET password = %s
            WHERE lower(email) = %s AND id_rol = 1
            """,
            (generate_password_hash(password), SUPERADMIN_ANCLA),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("No se encontró exactamente una cuenta ancla")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    restablecer_contrasena_superadmin()
    print("Contraseña del superadministrador actualizada.")

from psycopg2.extras import RealDictCursor
from interfaces.login_repository import ILoginRepository
from interfaces.usuario_repository import IUsuarioRepository

ROL_DOCENTE = 3


# las reservas buscan el nombre en la tabla docente, por eso el docente
# tiene que quedar alli con el mismo id que tiene en usuario
def _guardar_docente(cursor, id_usuario):
    cursor.execute(
        """
        INSERT INTO docente (id_docente, nombre, correo, telefono)
        SELECT u.id_usuario, u.nombre, u.email, 'Sin Teléfono'
        FROM usuario u
        WHERE u.id_usuario = %s
          AND NOT EXISTS (SELECT 1 FROM docente d WHERE d.id_docente = u.id_usuario)
        """,
        (id_usuario,),
    )
    cursor.execute(
        "SELECT setval(pg_get_serial_sequence('docente', 'id_docente'), "
        "GREATEST((SELECT MAX(id_docente) FROM docente), 1), true)"
    )


class PostgresUsuarioRepository(IUsuarioRepository, ILoginRepository):
    def __init__(self, connection_factory):
        self._connection_factory = connection_factory

    def crear(self, nombre, email, password_hash, id_rol, estado="activo"):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO usuario (nombre, email, password, id_rol, estado)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id_usuario
                    """,
                    (nombre, email, password_hash, id_rol, estado or "activo"),
                )
            except Exception:
                conn.rollback()
                cursor.execute(
                    """
                    INSERT INTO usuario (nombre, email, password, id_rol)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id_usuario
                    """,
                    (nombre, email, password_hash, id_rol),
                )
            fila = cursor.fetchone()
            id_usuario = fila["id_usuario"] if isinstance(fila, dict) else fila[0]
            if id_rol == ROL_DOCENTE:
                _guardar_docente(cursor, id_usuario)
            conn.commit()
        finally:
            conn.close()

    def actualizar_password(self, email, password_hash):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE usuario SET password = %s WHERE lower(email) = lower(%s)",
                (password_hash, email),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def listar(self):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute(
                    "SELECT id_usuario, nombre, email, id_rol, estado FROM usuario ORDER BY id_usuario"
                )
            except Exception:
                cursor.execute(
                    "SELECT id_usuario, nombre, email, id_rol FROM usuario ORDER BY id_usuario"
                )
            return cursor.fetchall()
        finally:
            conn.close()

    def buscar_por_id(self, id_usuario):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute(
                    "SELECT id_usuario, nombre, email, id_rol, estado FROM usuario WHERE id_usuario = %s",
                    (id_usuario,),
                )
            except Exception:
                cursor.execute(
                    "SELECT id_usuario, nombre, email, id_rol FROM usuario WHERE id_usuario = %s",
                    (id_usuario,),
                )
            return cursor.fetchone()
        finally:
            conn.close()

    def buscar_por_email(self, email):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos de Supabase")
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM usuario WHERE lower(email) = lower(%s)",
                (email,),
            )
            return cursor.fetchone()
        finally:
            conn.close()

    def actualizar_rol(self, id_usuario, id_rol):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE usuario SET id_rol = %s, estado = 'activo' WHERE id_usuario = %s",
                    (id_rol, id_usuario),
                )
            except Exception:
                conn.rollback()
                cursor.execute(
                    "UPDATE usuario SET id_rol = %s WHERE id_usuario = %s",
                    (id_rol, id_usuario),
                )
            actualizado = cursor.rowcount > 0
            if actualizado and id_rol == ROL_DOCENTE:
                _guardar_docente(cursor, id_usuario)
            conn.commit()
            return actualizado
        finally:
            conn.close()

    def eliminar(self, id_usuario):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cola_espera WHERE id_docente = %s", (id_usuario,))
            cursor.execute("DELETE FROM reserva WHERE id_docente = %s", (id_usuario,))
            cursor.execute("DELETE FROM docente WHERE id_docente = %s", (id_usuario,))
            cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

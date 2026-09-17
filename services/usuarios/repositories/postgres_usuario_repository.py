from interfaces.usuario_repository import IUsuarioRepository


class PostgresUsuarioRepository(IUsuarioRepository):
    def __init__(self, connection_factory):
        self._connection_factory = connection_factory

    def crear(self, nombre, email, password_hash, id_rol):
        conn = self._connection_factory()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO usuario (nombre, email, password, id_rol)
                VALUES (%s, %s, %s, %s)
                """,
                (nombre, email, password_hash, id_rol),
            )
            conn.commit()
        finally:
            conn.close()

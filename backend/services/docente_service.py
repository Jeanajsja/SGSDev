from database.db_config import get_connection
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

class DocenteService:
    def listar(self):
        conn = get_connection()
        if conn is None: return []
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id_usuario as id_docente, nombre, email as correo, 'Sin Teléfono' as telefono
                FROM usuario 
                WHERE id_rol = 3 
                ORDER BY nombre ASC
            """)
            data = cursor.fetchall()
            conn.close()
            return data
        except Exception as e:
            if conn: conn.close()
            return []

    def crear(self, data):
        conn = get_connection()
        if conn is None: return {"status": "error", "message": "Error de conexión"}
        try:
            cursor = conn.cursor()
            password_defecto = generate_password_hash("docente123")
            cursor.execute("""
                INSERT INTO usuario (nombre, email, password, id_rol) 
                VALUES (%s, %s, %s, 3)
            """, (data['nombre'], data['correo'], password_defecto))
            conn.commit()
            conn.close()
            return {"status": "ok", "message": "Docente registrado con éxito. Contraseña por defecto: docente123"}
        except Exception as e:
            if conn: conn.close()
            return {"status": "error", "message": f"Error al registrar docente: {str(e)}"}
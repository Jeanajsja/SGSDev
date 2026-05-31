from database.db_config import get_connection
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash # Para seguridad

class UsuarioService:
    # Tarea 8 y 9: Registrar usuarios (Admin, Operador, Docente)
    def crear_usuario(self, data):
        conn = get_connection()
        if not conn: return {"status": "error", "message": "Error de conexión"}
        
        try:
            cursor = conn.cursor()
            # Encriptamos la contraseña antes de guardarla
            password_segura = generate_password_hash(data['password'])
            
            query = """
                INSERT INTO usuario (nombre, email, password, id_rol) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (data['nombre'], data['email'], password_segura, data['id_rol']))
            conn.commit()
            conn.close()
            return {"status": "ok", "message": "Cuenta creada exitosamente"}
        except Exception as e:
            if conn: conn.close()
            return {"status": "error", "message": f"El correo ya existe o hay un error: {str(e)}"}
    def login(self, email, password):
        conn = get_connection()
        
        if conn is None:
            return {"status": "error", "message": "No se pudo conectar a la base de datos de Supabase"}
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM usuario WHERE email = %s", (email,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                # Verificación híbrida: soporta texto plano y hash seguro de werkzeug
                valido = False
                if user['password'] == password:
                    valido = True
                else:
                    try:
                        valido = check_password_hash(user['password'], password)
                    except Exception:
                        valido = False
                
                if valido:
                    # Limpiar password para no exponerlo en el frontend
                    user_clean = dict(user)
                    user_clean.pop('password', None)
                    return {"status": "ok", "user": user_clean}
            
            return {"status": "error", "message": "Credenciales inválidas"}
        except Exception as e:
            if conn: conn.close()
            return {"status": "error", "message": f"Error en el servidor: {str(e)}"}
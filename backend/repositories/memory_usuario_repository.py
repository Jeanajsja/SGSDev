from interfaces.usuario_repository import IUsuarioRepository


class MemoryUsuarioRepository(IUsuarioRepository):
    def __init__(self):
        self._usuarios = []
        self._next_id = 1

    def crear(self, nombre, email, password_hash, id_rol):
        if any(u["email"] == email for u in self._usuarios):
            raise Exception("duplicate key")
        self._usuarios.append(
            {
                "id_usuario": self._next_id,
                "nombre": nombre,
                "email": email,
                "password": password_hash,
                "id_rol": id_rol,
            }
        )
        self._next_id += 1

    def buscar_por_email(self, email):
        return next((u.copy() for u in self._usuarios if u["email"] == email), None)

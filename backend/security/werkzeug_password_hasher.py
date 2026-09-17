from werkzeug.security import check_password_hash, generate_password_hash
from interfaces.password_hasher import IPasswordHasher


class WerkzeugPasswordHasher(IPasswordHasher):
    """LSP: sustituye a IPasswordHasher. OCP: se puede cambiar por bcrypt sin tocar servicios."""

    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verificar(self, password: str, almacenado: str) -> bool:
        if almacenado == password:
            return True
        try:
            return check_password_hash(almacenado, password)
        except Exception:
            return False

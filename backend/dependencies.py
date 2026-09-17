from database.db_config import get_connection
from repositories.postgres_usuario_repository import PostgresUsuarioRepository
from security.werkzeug_password_hasher import WerkzeugPasswordHasher
from services.usuario_service import UsuarioService


def get_usuario_service() -> UsuarioService:
    return UsuarioService(PostgresUsuarioRepository(get_connection), WerkzeugPasswordHasher())

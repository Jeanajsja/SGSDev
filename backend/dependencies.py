from database.db_config import get_connection
from repositories.postgres_reserva_repository import PostgresReservaRepository
from repositories.postgres_rol_repository import PostgresRolRepository
from repositories.postgres_usuario_repository import PostgresUsuarioRepository
from security.werkzeug_password_hasher import WerkzeugPasswordHasher
from services.reserva_service import ReservaService
from services.rol_service import RolService
from services.usuario_service import UsuarioService


def get_usuario_service() -> UsuarioService:
    return UsuarioService(PostgresUsuarioRepository(get_connection), WerkzeugPasswordHasher())


def get_reserva_service() -> ReservaService:
    return ReservaService(PostgresReservaRepository(get_connection))


def get_rol_service() -> RolService:
    return RolService(PostgresRolRepository(get_connection))

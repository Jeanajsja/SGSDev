from .login_service import LoginService
from .repositories.postgres_login_repository import PostgresLoginRepository
from ..security.werkzeug_password_hasher import WerkzeugPasswordHasher
from .db_config import get_connection


def get_login_service():
    """FastAPI dependency that builds a LoginService with a Postgres repository.
    The repository receives the existing ``get_connection`` factory, preserving the
    current DB‑connection logic.
    """
    repository = PostgresLoginRepository(get_connection)
    hasher = WerkzeugPasswordHasher()
    return LoginService(repository, hasher)

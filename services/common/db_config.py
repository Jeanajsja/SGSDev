import logging
import os

import psycopg2


logger = logging.getLogger(__name__)


def get_connection():
    required = ("DB_HOST", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Faltan variables de conexión a Supabase: " + ", ".join(missing)
        )

    try:
        return psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=int(os.getenv("DB_PORT", "6543")),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            sslmode=os.getenv("DB_SSLMODE", "require"),
            connect_timeout=5,
        )
    except (psycopg2.Error, ValueError) as error:
        logger.exception("No se pudo conectar a Supabase PostgreSQL")
        raise ConnectionError(
            "No se pudo conectar a Supabase; verifica DB_HOST, DB_PORT, "
            "DB_USER, DB_PASSWORD y DB_SSLMODE"
        ) from error

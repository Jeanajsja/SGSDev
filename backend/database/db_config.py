import logging
import os
import socket
import threading
import time

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool


logger = logging.getLogger(__name__)
_lock = threading.Lock()
_pool = None
_hostaddr = None
_keepalive_started = False


def _resolve_hostaddr(host, port):
    """Resuelve el host una vez para evitar DNS lento/fallido en cada conexión (Kind)."""
    global _hostaddr
    if _hostaddr:
        return _hostaddr
    pinned = (os.getenv("DB_HOSTADDR") or "").strip()
    if pinned:
        _hostaddr = pinned
        logger.info("DB hostaddr fijado por DB_HOSTADDR=%s", pinned)
        return _hostaddr
    last_error = None
    for intento in range(1, 5):
        try:
            infos = socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
            if not infos:
                raise OSError(f"Sin direcciones para {host}")
            _hostaddr = infos[0][4][0]
            logger.info("DB host %s resuelto a %s", host, _hostaddr)
            return _hostaddr
        except OSError as error:
            last_error = error
            logger.warning("DNS DB falló (intento %s/4): %s", intento, error)
            time.sleep(0.4 * intento)
    raise ConnectionError(f"No se pudo resolver {host}") from last_error


def _connect_kwargs():
    required = ("DB_HOST", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Faltan variables de conexión a Supabase: " + ", ".join(missing)
        )
    host = os.environ["DB_HOST"]
    port = int(os.getenv("DB_PORT", "6543"))
    kwargs = {
        "host": host,
        "port": port,
        "database": os.getenv("DB_NAME", "postgres"),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "sslmode": os.getenv("DB_SSLMODE", "require"),
        "cursor_factory": RealDictCursor,
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
    try:
        kwargs["hostaddr"] = _resolve_hostaddr(host, port)
    except Exception as error:
        logger.warning("Continuando sin hostaddr cacheado: %s", error)
    return kwargs


def _ensure_pool():
    global _pool
    if _pool is not None:
        return _pool
    with _lock:
        if _pool is not None:
            return _pool
        last_error = None
        for intento in range(1, 4):
            try:
                kwargs = _connect_kwargs()
                minconn = int(os.getenv("DB_POOL_MIN", "1"))
                maxconn = int(os.getenv("DB_POOL_MAX", "6"))
                _pool = ThreadedConnectionPool(minconn, maxconn, **kwargs)
                return _pool
            except (psycopg2.Error, ValueError, OSError, ConnectionError) as error:
                last_error = error
                logger.warning("Pool Supabase falló (intento %s/3): %s", intento, error)
                time.sleep(0.35 * intento)
        logger.exception("No se pudo crear el pool hacia Supabase")
        raise ConnectionError(
            "No se pudo conectar a Supabase; verifica DB_HOST, DB_PORT, "
            "DB_USER, DB_PASSWORD y DB_SSLMODE"
        ) from last_error


class _PooledConnection:
    """Devuelve la conexión al pool en close(); rollback suave entre usos."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        conn = self._conn
        self._conn = None
        if conn is None:
            return
        try:
            if getattr(conn, "closed", 1) == 0:
                conn.rollback()
            pool = _pool
            if pool is not None:
                pool.putconn(conn)
            else:
                conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def get_connection():
    try:
        pool = _ensure_pool()
        return _PooledConnection(pool.getconn())
    except Exception:
        last_error = None
        for intento in range(1, 4):
            try:
                return psycopg2.connect(**_connect_kwargs())
            except (psycopg2.Error, ValueError, OSError) as error:
                last_error = error
                time.sleep(0.35 * intento)
        raise ConnectionError("No se pudo conectar a Supabase") from last_error


def warm_connection():
    """Abre una conexión del pool y hace ping (amortiza TLS/DNS al arranque)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()


def start_keepalive(interval_sec=25):
    """Mantiene el pool caliente para evitar reconexiones lentas a Supabase."""
    global _keepalive_started
    with _lock:
        if _keepalive_started:
            return
        _keepalive_started = True

    def _loop():
        while True:
            try:
                warm_connection()
            except Exception as error:
                logger.warning("Keepalive DB falló: %s", error)
            time.sleep(max(10, int(interval_sec)))

    threading.Thread(target=_loop, name="db-keepalive", daemon=True).start()

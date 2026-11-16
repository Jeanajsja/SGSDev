import os

import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    required = ("DB_HOST", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Faltan variables de conexión a Supabase: " + ", ".join(missing)
        )

    params = {
        "host": os.environ["DB_HOST"],
        "port": int(os.getenv("DB_PORT", "6543")),
        "database": os.getenv("DB_NAME", "postgres"),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "sslmode": os.getenv("DB_SSLMODE", "require"),
        "connect_timeout": 5
    }
    
    try:
        conn = psycopg2.connect(**params)
        return conn
    except Exception as e:
        print(f"\n[ERROR] Connection failed completely: {e}\n")
        return None
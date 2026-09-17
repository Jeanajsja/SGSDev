import os
import sys

# Agregar la carpeta backend al PATH para que Gunicorn/Uvicorn encuentre
# todos los módulos internos (controllers, services, database)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from main import app

# Arranque local:  python -m uvicorn wsgi:app --reload --port 5000
# Producción:     gunicorn -k uvicorn.workers.UvicornWorker wsgi:app --bind 0.0.0.0:5000

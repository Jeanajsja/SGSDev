import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
# para que uvicorn/gunicorn encuentren controllers, services, etc.
sys.path.insert(0, os.path.join(_ROOT, "backend"))
sys.path.insert(0, os.path.join(_ROOT, "services"))

from main import app

# local: python -m uvicorn wsgi:app --reload --port 5000
# server: gunicorn -k uvicorn.workers.UvicornWorker wsgi:app --bind 0.0.0.0:5000


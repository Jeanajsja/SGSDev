import os
import sys

# Agregar la carpeta backend al PATH para que Python encuentre los controladores y servicios correctamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from backend.main import app

if __name__ == "__main__":
    app.run()

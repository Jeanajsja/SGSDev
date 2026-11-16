# SGSDev

Sistema para gestionar salones y reservas.

Backend en FastAPI, pantallas en HTML/JS.

## MVC

- **Modelo:** `backend/models`, `services` y `repositories`
- **Vista:** `frontend/templates` y `frontend/static`
- **Controlador:** `backend/controllers`

El monolito ya no tiene APIs. Solo sirve las pantallas. Todo el ruteo lo hace el gateway.

- `/api/login` -> ms-login
- `/api/salones` -> ms-salones
- `/api/docentes` -> ms-docentes
- `/api/roles` -> ms-roles
- `/api/usuarios` -> ms-usuarios
- `/api/reservas` -> ms-reservas

Para levantar todo:

```
cp -n .env.example .env
# Completa DB_* con las credenciales PostgreSQL de tu proyecto Supabase.
# Genera JWT_SECRET con `openssl rand -hex 32` y guárdalo solo en .env.
# SUPERADMIN_PASSWORD se usa solo para aprovisionar la cuenta ancla si aún no existe.
# Vincula el proyecto con: supabase link --project-ref <project-ref>
supabase db push
docker compose up --build
```

La app entra por http://localhost:8080

El registro público solo crea cuentas de docente. La creación y administración de
otros roles requiere autenticación y permisos en el servidor. Las sesiones usan
tokens Bearer firmados y de corta duración. No compartas ni subas `.env`.

Si la cuenta ancla ya existe, el arranque no cambia su contraseña ni sus datos.
Para rotar la contraseña de esa cuenta, define temporalmente `SUPERADMIN_PASSWORD`
en `.env`, ejecuta `docker compose run --rm login python reset_superadmin_password.py`
y elimina esa variable de `.env` al terminar. Para el primer aprovisionamiento,
la misma variable crea la cuenta si no existe; también debe eliminarse después.

El manifiesto Kubernetes con credenciales fue retirado porque estaba versionado.
El script `k8s/desplegar.ps1` crea el Secret desde `.env`; nunca publiques ese
archivo. Como la credencial anterior estuvo en el historial Git, rótala en Supabase
y actualiza `DB_PASSWORD` antes de desplegar. La eliminación del manifiesto no
borra sus versiones anteriores del historial Git.

Las migraciones de `supabase/migrations/` crean las tablas de la aplicación y
`historial_usuario`. Este historial registra automáticamente altas, cambios de
datos (incluido el rol) y eliminaciones de usuarios; no guarda contraseñas ni
sus hashes.
Todos los servicios guardan y consultan los datos en PostgreSQL de Supabase
mediante las variables `DB_*`; no usan almacenamiento en memoria en producción.
Para Render usa los datos de **Transaction pooler** del panel de Supabase:
`DB_HOST`, puerto `6543`, `DB_USER` exacto del panel (incluye el identificador
del proyecto), `DB_PASSWORD` de PostgreSQL, `DB_NAME=postgres` y
`DB_SSLMODE=require`. En local puedes usar la conexión directa (`5432`, usuario
`postgres`) si tu red permite IPv6. Nunca subas `.env` a Git.
Aplica el esquema con `supabase db push` antes de usar la aplicación.

## SOLID

- **S:** cada servicio hace una sola cosa. Login no registra usuarios.
- **O:** el servicio no cambia si pongo otro repositorio. Hay uno de memoria para las pruebas.
- **L:** superadministrador y administrador heredan de usuario y se pueden usar igual.
- **I:** el login solo pide verificar la clave. El registro solo pide hashearla.
- **D:** los servicios dependen de interfaces, no de Postgres ni de Werkzeug.

Los controladores no hablan con la base de datos. Por eso se puede probar sin internet.

Para correrlo:

```
pip install -r requirements.txt
python -m uvicorn wsgi:app --reload --port 5000
```

Tests:

```
python -m unittest backend.tests.test_solid -v
```

Documentacion de la API: http://localhost:5000/docs

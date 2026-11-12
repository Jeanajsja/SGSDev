import os, glob
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Artifact directory where images and the PPT will be stored
artifact_dir = r"C:\Users\Usuario\.gemini\antigravity\brain\23d5e82b-edbe-4f69-9d80-bd4dd3e06b65"
output_path = os.path.join(artifact_dir, "SGSDev_Presentation_Final.pptx")

def add_slide(prs, title, bullet_points=None, img_path=None):
    """Create a slide with a title, optional bullet points and optional picture.
    Fonts are set a bit larger for a presentation setting.
    """
    slide_layout = prs.slide_layouts[1]  # Title + Content layout
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = title
    if bullet_points:
        tf = slide.placeholders[1].text_frame
        tf.clear()
        for point in bullet_points:
            p = tf.add_paragraph()
            p.text = point
            p.font.size = Pt(18)
            p.level = 0
    if img_path and os.path.isfile(img_path):
        # Insert picture, roughly centered
        left = Inches(1)
        top = Inches(2)
        width = Inches(8)
        slide.shapes.add_picture(img_path, left, top, width=width)
    return slide

prs = Presentation()

# ---------------------------------------------------------------------
# Slide 1 – Cover (Title Slide)
# ---------------------------------------------------------------------
slide = prs.slides.add_slide(prs.slide_layouts[0])  # Title Slide layout
slide.shapes.title.text = "SGSDev – Sistema de Gestión de Salones"
subtitle = slide.placeholders[1]
subtitle.text = "Universidad Católica de Colombia – 2026\nMigración monolito → micro‑servicios (Patrón Strangler)"
for paragraph in subtitle.text_frame.paragraphs:
    paragraph.font.size = Pt(24)

# ---------------------------------------------------------------------
# Slide 2 – Descripción del proyecto (expanded)
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Descripción del proyecto",
    [
        "Aplicación web que permite registrar salones, docentes y gestionar reservas de manera centralizada.",
        "Control de conflictos de horario mediante una cola de espera FIFO que garantiza el orden de llegada.",
        "Gestión de usuarios basada en roles (Super‑admin, Administrador, Docente) con permisos granulares."
    ]
)

# ---------------------------------------------------------------------
# Slide 3 – Roles del sistema (expanded)
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Roles del sistema",
    [
        "Superadministrador: Aprobar/cambiar roles, eliminar cuentas, crear nuevos super‑admins. Cuenta ancla (lfpaez30@ucatolica.edu.co) es la única con este poder.",
        "Administrador: Crear, modificar y eliminar salones, docentes y reservas. Tiene visión completa del calendario.",
        "Docente: Consultar disponibilidad de salones y crear reservas. Sólo interactúa con su propio horario."
    ]
)

# ---------------------------------------------------------------------
# Slide 4 – Tecnologías utilizadas (expanded)
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Tecnologías utilizadas",
    [
        "Python 3.11 – lenguaje principal del backend.",
        "FastAPI – framework web moderno, generación automática de documentación Swagger y validación con Pydantic.",
        "Jinja2, HTML, Tailwind CSS, JavaScript – capa de presentación del monolito.",
        "PostgreSQL (Supabase) con psycopg2 – base de datos SaaS.",
        "Werkzeug – funciones de hashing y verificación de contraseñas.",
        "Gunicorn + Uvicorn – servidor ASGI para cada micro‑servicio.",
        "Nginx – API‑Gateway que expone un único punto de entrada (puerto 8080).",
        "Docker + Docker‑Compose – un contenedor por micro‑servicio, facilitando despliegue y escalado.",
        "unittest – pruebas unitarias que garantizan el cumplimiento de SOLID."
    ]
)

# ---------------------------------------------------------------------
# Slide 5 – Decisiones clave (expanded)
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Branch By Abstraction",
    [
        "Técnica de refactorización que permite introducir una nueva capa de abstracción antes de mover código a micro‑servicios.",
        "Facilita la migración gradual: el código nuevo llama a la abstracción y el monolito sigue funcionando.",
        "Permite pruebas y despliegues independientes de la nueva capa.",
        "Se utilizó para separar la lógica de negocio del monolito antes de crear los micro‑servicios."
    ]
)


# ---------------------------------------------------------------------
# Slide 6 – Arquitectura de micro‑servicios (with diagram)
# ---------------------------------------------------------------------
# Locate the generated architecture diagram image
arch_images = glob.glob(os.path.join(artifact_dir, "sgsdev_architecture_*.jpg"))
arch_path = arch_images[0] if arch_images else None
add_slide(
    prs,
    "Arquitectura de micro‑servicios",
    [
        "Nginx (API‑Gateway) en puerto 8080 recibe todas las peticiones del navegador.",
        "Seis micro‑servicios FastAPI (login, salones, docentes, roles, usuarios, reservas) escuchan en puertos 5001‑5006.",
        "Monolito (puerto 5000) sirve únicamente HTML, CSS y JavaScript estáticos.",
        "Todos comparten la misma base de datos Supabase, pero cada servicio interactúa solo con su tabla."
    ],
    img_path=arch_path,
)

# ---------------------------------------------------------------------
# Slide 7 – Organización MVC
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Organización MVC",
    [
        "Modelo: `backend/models/` – entidades, servicios y repositorios.",
        "Vista: `frontend/templates/` + `frontend/static/` – plantillas Jinja2, CSS Tailwind y scripts JS.",
        "Controlador: `backend/controllers/` – `vista_controller.py` para el monolito y `*_controller.py` para cada micro‑servicio."
    ]
)

# ---------------------------------------------------------------------
# Slide 8 – Principios SOLID
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Principios SOLID",
    [
        "S – Responsabilidad única: cada clase/servicio posee una única responsabilidad bien definida.",
        "O – Abierto/Cerrado: los componentes pueden extenderse (ej. nuevos repositorios) sin modificar código existente.",
        "L – Sustitución de Liskov: subclases como `Superadmin` y `Administrador` pueden usarse donde se espera un `Usuario`.",
        "I – Segregación de interfaces: interfaces pequeñas (`IPasswordHasher`, `IEmailValidator`) evitan dependencias innecesarias.",
        "D – Inversión de dependencias: los servicios reciben sus dependencias mediante inyección (`Depends()` de FastAPI)."
    ]
)

# ---------------------------------------------------------------------
# Slide 9 – Patrones de diseño
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Patrones de diseño",
    [
        "Strangler – migración incremental del monolito a micro‑servicios.",
        "API Gateway – Nginx centraliza la exposición de APIs.",
        "Repository – separación de la lógica de acceso a datos (`*_repository.py`).",
        "Dependency Injection – `dependencies.py` + FastAPI `Depends()`.",
        "Strategy – `IPasswordHasher`, `IEmailValidator` permiten intercambiar algoritmos.",
        "Factory – `usuario_factory.py`, `create_app()`, `connection_factory` crean instancias según contexto.",
        "FIFO Queue – `reserva_service.py` y tabla `cola_espera` gestionan reservas en orden de llegada."
    ]
)

# ---------------------------------------------------------------------
# Slide 10 – Docker & Docker‑Compose
# ---------------------------------------------------------------------
add_slide(
    prs,
    "Docker & Docker‑Compose",
    [
        "Archivo `docker‑compose.yml` describe todos los contenedores: gateway, monolito y los seis micro‑servicios.",
        "Cada micro‑servicio tiene su propio `Dockerfile` y puerto dedicado (5001‑5006).",
        "Ventajas: aislamiento de procesos, despliegues reproducibles, escalado por servicio y facilidad de pruebas locales."
    ]
)

# Save the enhanced presentation
prs.save(output_path)
print(f"Presentation saved to {output_path}")

from pptx import Presentation
from pptx.util import Inches, Pt

# Path to save the PowerPoint in the artifact directory
artifact_dir = r"C:\Users\Usuario\.gemini\antigravity\brain\23d5e82b-edbe-4f69-9d80-bd4dd3e06b65"
output_path = os.path.join(artifact_dir, "SGSDev_Presentation.pptx")

def add_slide(prs, title, bullet_points=None):
    slide_layout = prs.slide_layouts[1]  # Title and Content
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = title
    if bullet_points:
        body_shape = slide.shapes.placeholders[1]
        tf = body_shape.text_frame
        # First bullet point
        tf.text = bullet_points[0]
        tf.paragraphs[0].font.size = Pt(14)
        # Remaining bullet points
        for point in bullet_points[1:]:
            p = tf.add_paragraph()
            p.text = point
            p.font.size = Pt(14)
    return slide

prs = Presentation()
# Slide 1: Portada
add_slide(prs, "SGSDev - Sistema de Gestión de Salones", ["Universidad Católica de Colombia", "2026", "Patrón Strangler: migración de monolito a micro‑servicios"])
# Slide 2: Descripción del proyecto
add_slide(prs, "Descripción del proyecto", ["Aplicación web para registrar salones, docentes y reservas", "Control de cruces de horario con cola de espera FIFO", "Gestión de usuarios por roles (Super‑admin, Administrador, Docente)"])
# Slide 3: Roles del sistema
add_slide(prs, "Roles del sistema", ["Superadministrador: Aprobar/cambiar roles, eliminar cuentas. Cuenta ancla lfpaez30@ucatolica.edu.co.", "Administrador: Gestionar salones, docentes y reservas.", "Docente: Consultar salones y crear reservas."])
# Slide 4: Tecnologías utilizadas
add_slide(prs, "Tecnologías utilizadas", ["Python 3.11", "FastAPI (framework web)", "Pydantic (validación)", "Jinja2 + HTML + Tailwind CSS + JavaScript (vistas del monolito)", "PostgreSQL (Supabase) con psycopg2", "Werkzeug (hash de contraseñas)", "Gunicorn + Uvicorn (servidor)", "Nginx (API Gateway)", "Docker + Docker‑Compose (un contenedor por micro‑servicio)", "unittest (tests)" ] )
# Slide 5: Decisiones clave
add_slide(prs, "Decisiones clave", ["Patrón Strangler: migración gradual sin downtime.", "FastAPI en vez de Flask: validación automática, docs Swagger, mejor rendimiento.", "Nginx como API‑Gateway: punto de entrada único (puerto 8080).", "Monolito solo entrega vistas, lógica en micro‑servicios.", "Un contenedor por micro‑servicio para aislamiento y escalado.", "Tablas por micro‑servicio; tabla docente separada y sincronizada.", "Cuenta super‑admin ancla, no borrable.", "Hash de contraseñas, nunca en texto plano.", "Validación de correos con sugerencias.", "Cola de espera FIFO para reservas conflictivas.", "Repositorios en memoria para pruebas unitarias."] )
# Slide 6: Arquitectura de micro‑servicios
add_slide(prs, "Arquitectura de micro‑servicios", ["Nginx (API‑Gateway) en puerto 8080 enruta a los micro‑servicios.", "Micro‑servicios FastAPI en puertos 5001‑5006 (login, salones, docentes, roles, usuarios, reservas).", "Monolito en puerto 5000 solo sirve HTML/JS.", "Todos comparten la misma base en Supabase."] )
# Slide 7: Organización MVC
add_slide(prs, "Organización MVC", ["Modelo: backend/models/ (entidades, servicios, repositorios).", "Vista: frontend/templates/ + frontend/static/ (HTML, CSS, JS).", "Controlador: backend/controllers/ (vista_controller.py y *_controller.py)."] )
# Slide 8: Principios SOLID
add_slide(prs, "Principios SOLID", ["S – Responsabilidad única: cada clase/servicio tiene una única función.", "O – Abierto/Cerrado: cambiar de base de datos creando nuevo repositorio.", "L – Sustitución de Liskov: subclases (Superadmin, Admin) pueden usarse donde se espera Usuario.", "I – Segregación de interfaces: interfaces pequeñas (IPasswordHasher, IEmailValidator).", "D – Inversión de dependencias: servicios reciben dependencias por inyección (Depends())."] )
# Slide 9: Patrones de diseño
add_slide(prs, "Patrones de diseño", ["Strangler: migración incremental.", "API Gateway (Nginx).", "Repository: interfaces *_repository.py + implementaciones.", "Dependency Injection (dependencies.py + FastAPI Depends()).", "Strategy (IPasswordHasher, IEmailValidator).", "Factory (usuario_factory.py, create_app()).", "FIFO Queue (reserva_service.py, tabla cola_espera)."] )
# Slide 10: Docker & Docker‑Compose (esquemático)
add_slide(prs, "Docker & Docker‑Compose", ["docker-compose.yml define servicios: gateway, monolito, ms‑login, ms‑salones, ms‑docentes, ms‑roles, ms‑usuarios, ms‑reservas.", "Cada micro‑servicio tiene su Dockerfile y puerto dedicado (5001‑5006).", "Un contenedor por servicio → aislamiento, reinicio y escalado independiente."] )

# Guardar la presentación
prs.save(output_path)
print(f"Presentation saved to {output_path}")

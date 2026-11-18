
import logging

logger = logging.getLogger(__name__)

CAPACIDAD_DEFAULT = 20
SALONES = [f"Salon{i}" for i in range(1, 11)]
LABS = [f"Lab{i}" for i in range(1, 11)]


def _nombres_base():
    return [(nombre, "Edificio principal") for nombre in SALONES] + [
        (nombre, "Laboratorios") for nombre in LABS
    ]


def asegurar_salones_base(connection_factory):
    # error intencional para fallar el Action (compileall)
    return {

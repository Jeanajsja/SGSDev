"""Almacén temporal de códigos PIN para restablecer contraseña."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_pins: dict[str, dict] = {}


def _ttl_segundos():
    return max(60, int(os.getenv("RESET_PIN_MINUTES", "15")) * 60)


def _hash_pin(pin: str) -> str:
    secreto = os.getenv("JWT_SECRET", "sgsdev")
    return hashlib.sha256(f"{secreto}:{pin}".encode("utf-8")).hexdigest()


def generar_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def guardar_pin(email: str, pin: str) -> None:
    correo = (email or "").strip().lower()
    if not correo:
        return
    with _lock:
        _pins[correo] = {
            "hash": _hash_pin(pin),
            "expira": time.time() + _ttl_segundos(),
            "intentos": 0,
        }


def verificar_y_consumir_pin(email: str, pin: str) -> bool:
    correo = (email or "").strip().lower()
    codigo = (pin or "").strip()
    if not correo or not codigo:
        return False
    with _lock:
        entrada = _pins.get(correo)
        if not entrada:
            return False
        if time.time() > float(entrada.get("expira") or 0):
            _pins.pop(correo, None)
            return False
        intentos = int(entrada.get("intentos") or 0) + 1
        entrada["intentos"] = intentos
        if intentos > 5:
            _pins.pop(correo, None)
            return False
        if entrada.get("hash") != _hash_pin(codigo):
            return False
        _pins.pop(correo, None)
        return True

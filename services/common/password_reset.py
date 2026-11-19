import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import jwt

_ISSUER = "sgsdev"
_PURPOSE = "password_reset"


def _jwt_secret():
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET debe configurarse con al menos 32 caracteres")
    return secret


def crear_token_restablecimiento(email, minutos=None):
    minutos = int(minutos or os.getenv("RESET_TOKEN_MINUTES", "30"))
    ahora = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(email).strip().lower(),
            "purpose": _PURPOSE,
            "iss": _ISSUER,
            "iat": ahora,
            "exp": ahora + timedelta(minutes=max(5, minutos)),
        },
        _jwt_secret(),
        algorithm="HS256",
    )


def decodificar_token_restablecimiento(token):
    try:
        claims = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "purpose"]},
        )
        if claims.get("purpose") != _PURPOSE:
            return None
        email = str(claims.get("sub") or "").strip().lower()
        return email or None
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None


def url_base_app():
    return (os.getenv("APP_BASE_URL") or "http://localhost:8080").rstrip("/")


def construir_enlace_restablecimiento(token):
    return f"{url_base_app()}/reset-password.html?token={quote(str(token), safe='')}"

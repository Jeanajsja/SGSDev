import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)
_ISSUER = "sgsdev"


def _jwt_secret():
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET debe configurarse con al menos 32 caracteres",
        )
    return secret


def crear_token_acceso(usuario, minutos=30):
    ahora = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(usuario["email"]).lower(),
            "id_usuario": int(usuario["id_usuario"]),
            "id_rol": int(usuario["id_rol"]),
            "iss": _ISSUER,
            "iat": ahora,
            "exp": ahora + timedelta(minutes=minutos),
        },
        _jwt_secret(),
        algorithm="HS256",
    )


def _decodificar_token(token):
    try:
        claims = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "id_usuario", "id_rol"]},
        )
        principal = {
            "id_usuario": int(claims["id_usuario"]),
            "email": str(claims["sub"]).lower(),
            "id_rol": int(claims["id_rol"]),
        }
        if principal["id_usuario"] <= 0 or principal["id_rol"] not in {1, 2, 3}:
            raise ValueError("Claims fuera de rango")
        return principal
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def usuario_opcional(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)):
    if credentials is None:
        return None
    return _decodificar_token(credentials.credentials)


def usuario_actual(principal=Depends(usuario_opcional)):
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def requiere_rol(*roles):
    def verificar_rol(principal=Depends(usuario_actual)):
        if principal["id_rol"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta operación",
            )
        return principal

    return verificar_rol

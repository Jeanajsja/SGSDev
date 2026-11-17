def validar_password(password):
    clave = password or ""
    if len(clave) < 8:
        return {"status": "error", "message": "La contraseña debe tener mínimo 8 caracteres"}
    if not any(c.isalpha() for c in clave):
        return {"status": "error", "message": "La contraseña debe incluir letras"}
    if not any(c.isdigit() for c in clave):
        return {"status": "error", "message": "La contraseña debe incluir números"}
    return None

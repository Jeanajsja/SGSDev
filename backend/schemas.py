from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str
    id_rol: int
    solicitante_email: Optional[str] = None


class OlvidePasswordRequest(BaseModel):
    email: str


class RestablecerPasswordRequest(BaseModel):
    token: str
    nueva_password: str
    confirmar_password: str


class SalonPayload(BaseModel):
    nombre: str
    capacidad: int
    ubicacion: str


class ReservaPayload(BaseModel):
    fecha: str
    hora_inicio: str
    hora_fin: Optional[str] = None
    id_salon: int
    id_clase: Optional[int] = None
    id_docente: Optional[int] = None

    def as_reserva_data(self) -> dict:
        data = self.model_dump()
        id_clase = data.get("id_clase") if data.get("id_clase") is not None else data.get("id_docente")
        if id_clase is None:
            raise ValueError("Se requiere el ID clase de la reserva")
        data["id_clase"] = id_clase
        data["id_docente"] = id_clase  # columna histórica en BD
        return data


class DocenteCreate(BaseModel):
    nombre: str
    correo: str
    telefono: Optional[str] = Field(default=None)

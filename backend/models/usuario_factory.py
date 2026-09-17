from models.administrador import Administrador
from models.operador import Operador
from models.usuario import Usuario


def usuario_desde_fila(row):
    data = dict(row)
    rol = data.get("id_rol")
    if rol == 1:
        return Administrador.from_row(data)
    if rol == 2:
        return Operador.from_row(data)
    return Usuario.from_row(data)

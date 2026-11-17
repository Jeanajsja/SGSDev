from datetime import datetime, timedelta
from interfaces.reserva_repository import IReservaRepository


class ReservaService:

    def __init__(self, repository: IReservaRepository):
        self._repository = repository

    def listar(self):
        try:
            data = [
                r
                for r in self._repository.listar_detalle()
                if (r.get("estado") or "").lower() != "cancelada"
            ]
            return {"status": "ok", "data": data}
        except ConnectionError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def crear_reserva(self, data):
        h_ini = data["hora_inicio"]
        h_fin = data.get("hora_fin")
        if not h_fin:
            try:
                t_ini = datetime.strptime(h_ini, "%H:%M")
                h_fin = (t_ini + timedelta(hours=2)).strftime("%H:%M")
            except Exception:
                h_fin = "22:00"

        try:
            if self._repository.existe_cruce(
                data["id_salon"], data["fecha"], h_ini, h_fin
            ):
                return self._suscribir_a_cola(data["id_salon"], data["id_docente"])
            self._repository.crear(data["fecha"], h_ini, h_fin, data["id_docente"], data["id_salon"])
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": f"Error al crear reserva: {str(e)}"}
        return {"status": "ok", "message": "Reserva confirmada en Supabase"}

    def actualizar_reserva(self, id_reserva, data):
        try:
            actualizadas = self._repository.actualizar(
                id_reserva,
                data["fecha"],
                data["hora_inicio"],
                data["hora_fin"],
                data["id_salon"],
                data["id_docente"],
            )
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": f"Error al actualizar reserva: {str(e)}"}
        if not actualizadas:
            return {"status": "error", "message": "No se encontró la reserva para actualizar"}
        return {"status": "ok", "message": "Reserva actualizada con éxito"}

    def cancelar_reserva(self, id_reserva):
        try:
            id_salon = self._repository.cancelar(id_reserva)
            if id_salon is None:
                return {"status": "error", "message": "No se encontró la reserva"}
            self._repository.promover_siguiente_cola(id_salon)
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "ok"}

    def _suscribir_a_cola(self, id_salon, id_docente):
        try:
            self._repository.encolar(id_salon, id_docente)
        except ConnectionError:
            return {"status": "error", "message": "Error de conexión"}
        except Exception as e:
            return {"status": "error", "message": f"Error al ingresar a cola: {str(e)}"}
        return {"status": "cola", "message": "Añadido a lista de espera FIFO"}

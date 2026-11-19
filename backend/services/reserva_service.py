from datetime import datetime, timedelta
from interfaces.reserva_repository import IReservaRepository

HORAS_MINIMAS_CANCELACION = 8
MAX_HORAS_CLASE = 2
MAX_HORAS_DIA = 8
MAX_HORAS_SEMANA = 46
MSG_OPERACION_FALLIDA = "No se pudo completar la operación. Intenta de nuevo."
MSG_TRASLAPE = (
    "No es posible realizar la reserva: el salón ya está ocupado "
    "en ese horario (las horas no pueden traslaparse)"
)
MSG_TRASLAPE_DOCENTE = (
    "No es posible realizar la reserva: el docente ya tiene una clase "
    "en ese horario (las horas no pueden traslaparse)"
)


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
        except ConnectionError:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        except Exception:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}

    def listar_salones_disponibles(self, fecha, hora_inicio, hora_fin, excluir_id=None):
        error_duracion = self._validar_duracion_clase(hora_inicio, hora_fin)
        if error_duracion:
            return error_duracion
        try:
            data = self._repository.listar_salones_disponibles(
                fecha, hora_inicio, hora_fin, excluir_id=excluir_id
            )
            return {"status": "ok", "data": data}
        except ConnectionError:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        except Exception:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}

    def crear_reserva(self, data):
        h_ini = data["hora_inicio"]
        h_fin = data.get("hora_fin")
        if not h_fin:
            try:
                t_ini = datetime.strptime(str(h_ini)[:5], "%H:%M")
                h_fin = (t_ini + timedelta(hours=MAX_HORAS_CLASE)).strftime("%H:%M")
            except Exception:
                h_fin = "22:00"

        error_duracion = self._validar_duracion_clase(h_ini, h_fin)
        if error_duracion:
            return error_duracion

        horas_nuevas = self._duracion_horas(h_ini, h_fin)
        error_carga = self._validar_carga(data["id_docente"], data["fecha"], horas_nuevas)
        if error_carga:
            return error_carga

        error_cruce = self._validar_sin_traslape(
            data["id_salon"], data["id_docente"], data["fecha"], h_ini, h_fin
        )
        if error_cruce:
            return error_cruce

        try:
            self._repository.crear(data["fecha"], h_ini, h_fin, data["id_docente"], data["id_salon"])
        except ConnectionError:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        except Exception:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        return {"status": "ok", "message": "Reserva creada con éxito"}

    def actualizar_reserva(self, id_reserva, data):
        error_duracion = self._validar_duracion_clase(data["hora_inicio"], data["hora_fin"])
        if error_duracion:
            return error_duracion

        horas_nuevas = self._duracion_horas(data["hora_inicio"], data["hora_fin"])
        error_carga = self._validar_carga(
            data["id_docente"], data["fecha"], horas_nuevas, excluir_id=id_reserva
        )
        if error_carga:
            return error_carga

        error_cruce = self._validar_sin_traslape(
            data["id_salon"],
            data["id_docente"],
            data["fecha"],
            data["hora_inicio"],
            data["hora_fin"],
            excluir_id=id_reserva,
        )
        if error_cruce:
            return error_cruce

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
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        except Exception:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        if not actualizadas:
            return {"status": "error", "message": "No se encontró la reserva para actualizar"}
        return {"status": "ok", "message": "Reserva actualizada con éxito"}

    def cancelar_reserva(self, id_reserva, principal=None, ahora=None):
        reserva = self._buscar(id_reserva)
        if not reserva:
            return {"status": "error", "message": "La reserva no existe"}
        if (reserva.get("estado") or "").lower() == "cancelada":
            return {"status": "error", "message": "La reserva ya está cancelada"}

        rol = int((principal or {}).get("id_rol") or 0)
        if rol == 3:
            if reserva.get("id_docente") != principal["id_usuario"]:
                return {"status": "error", "message": "No puedes cancelar esta reserva"}

        # Admin y superadmin pueden cancelar sin la regla de anticipación.
        if rol not in (1, 2):
            momento = ahora or datetime.now()
            inicio = self._inicio_reserva(reserva)
            if inicio - momento < timedelta(hours=HORAS_MINIMAS_CANCELACION):
                return {
                    "status": "error",
                    "message": (
                        f"Solo se puede cancelar con al menos "
                        f"{HORAS_MINIMAS_CANCELACION} horas de anticipación"
                    ),
                }

        try:
            id_salon = self._repository.cancelar(id_reserva)
            if id_salon is None:
                return {"status": "error", "message": "No se encontró la reserva"}
            self._repository.promover_siguiente_cola(id_salon)
        except ConnectionError:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        except Exception:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        return {"status": "ok", "message": "Reserva cancelada con éxito"}

    def _suscribir_a_cola(self, id_salon, id_docente):
        try:
            self._repository.encolar(id_salon, id_docente)
        except ConnectionError:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        except Exception:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        return {"status": "cola", "message": "Añadido a lista de espera"}

    def _buscar(self, id_reserva):
        for r in self._repository.listar_detalle():
            if r.get("id_reserva") == id_reserva:
                return r
        return None

    def _inicio_reserva(self, reserva):
        fecha = str(reserva["fecha"])
        hora = str(reserva["hora_inicio"])[:5]
        return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")

    def _duracion_horas(self, hora_inicio, hora_fin):
        t_ini = datetime.strptime(str(hora_inicio)[:5], "%H:%M")
        t_fin = datetime.strptime(str(hora_fin)[:5], "%H:%M")
        return max((t_fin - t_ini).total_seconds() / 3600.0, 0)

    def _validar_duracion_clase(self, hora_inicio, hora_fin):
        horas = self._duracion_horas(hora_inicio, hora_fin)
        if horas <= 0:
            return {
                "status": "error",
                "message": "No es posible realizar la reserva: la hora de fin debe ser mayor que la de inicio",
            }
        if horas > MAX_HORAS_CLASE:
            return {
                "status": "error",
                "message": (
                    "No es posible realizar la reserva: una clase no puede durar más de "
                    f"{MAX_HORAS_CLASE} horas"
                ),
            }
        return None

    def _validar_sin_traslape(
        self, id_salon, id_docente, fecha, hora_inicio, hora_fin, excluir_id=None
    ):
        try:
            if self._repository.existe_cruce(
                id_salon, fecha, hora_inicio, hora_fin, excluir_id=excluir_id
            ):
                return {"status": "error", "message": MSG_TRASLAPE}
            if self._repository.existe_cruce_docente(
                id_docente, fecha, hora_inicio, hora_fin, excluir_id=excluir_id
            ):
                return {"status": "error", "message": MSG_TRASLAPE_DOCENTE}
        except ConnectionError:
            return {"status": "error", "message": MSG_OPERACION_FALLIDA}
        return None

    def _validar_carga(self, id_docente, fecha, horas_nuevas, excluir_id=None):
        activas = [
            r
            for r in self._repository.listar_detalle()
            if r.get("id_docente") == id_docente
            and (r.get("estado") or "").lower() != "cancelada"
            and (excluir_id is None or r.get("id_reserva") != excluir_id)
        ]
        inicio_semana = self._lunes_de(fecha)
        fin_semana = inicio_semana + timedelta(days=6)
        horas_por_dia = {}
        for r in activas:
            dia = datetime.strptime(str(r["fecha"])[:10], "%Y-%m-%d").date()
            if inicio_semana <= dia <= fin_semana:
                clave = str(r["fecha"])[:10]
                horas_por_dia[clave] = horas_por_dia.get(clave, 0.0) + self._duracion_horas(
                    r["hora_inicio"], r["hora_fin"]
                )

        fecha_clave = str(fecha)[:10]
        total_dia = horas_por_dia.get(fecha_clave, 0.0) + horas_nuevas
        if total_dia > MAX_HORAS_DIA:
            return {
                "status": "error",
                "message": (
                    "No es posible realizar la reserva: solo se pueden agendar máximo "
                    f"{MAX_HORAS_DIA} horas al día"
                ),
            }

        horas_semana = sum(horas_por_dia.values())
        if horas_semana + horas_nuevas > MAX_HORAS_SEMANA:
            return {
                "status": "error",
                "message": (
                    "No es posible realizar la reserva: no se pueden agendar más de "
                    f"{MAX_HORAS_SEMANA} horas semanales"
                ),
            }
        return None

    def _lunes_de(self, fecha):
        dia = datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()
        return dia - timedelta(days=dia.weekday())

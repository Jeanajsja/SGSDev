from datetime import datetime, timedelta
from interfaces.reserva_repository import IReservaRepository

HORAS_MINIMAS_CANCELACION = 8
MAX_HORAS_DIA = 8
MAX_HORAS_DIA_EXTENDIDO = 10
MAX_DIAS_EXTENDIDOS = 2
MAX_HORAS_SEMANA = 46


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

        horas_nuevas = self._duracion_horas(h_ini, h_fin)
        error_carga = self._validar_carga(data["id_docente"], data["fecha"], horas_nuevas)
        if error_carga:
            return error_carga

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

    def cancelar_reserva(self, id_reserva, ahora=None):
        reserva = self._buscar(id_reserva)
        if not reserva:
            return {"status": "error", "message": "La reserva no existe"}
        if (reserva.get("estado") or "").lower() == "cancelada":
            return {"status": "error", "message": "La reserva ya está cancelada"}

        momento = ahora or datetime.now()
        inicio = self._inicio_reserva(reserva)
        if inicio - momento < timedelta(hours=HORAS_MINIMAS_CANCELACION):
            return {
                "status": "error",
                "message": f"Solo se puede cancelar con al menos {HORAS_MINIMAS_CANCELACION} horas de anticipación",
            }

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

    def _validar_carga(self, id_docente, fecha, horas_nuevas):
        activas = [
            r
            for r in self._repository.listar_detalle()
            if r.get("id_docente") == id_docente and (r.get("estado") or "").lower() != "cancelada"
        ]
        inicio_semana = self._lunes_de(fecha)
        fin_semana = inicio_semana + timedelta(days=6)
        horas_por_dia = {}
        for r in activas:
            dia = datetime.strptime(str(r["fecha"]), "%Y-%m-%d").date()
            if inicio_semana <= dia <= fin_semana:
                clave = str(r["fecha"])
                horas_por_dia[clave] = horas_por_dia.get(clave, 0.0) + self._duracion_horas(
                    r["hora_inicio"], r["hora_fin"]
                )

        horas_dia = horas_por_dia.get(str(fecha), 0.0)
        total_dia = horas_dia + horas_nuevas
        if total_dia > MAX_HORAS_DIA_EXTENDIDO:
            return {
                "status": "error",
                "message": f"El docente no puede agendar más de {MAX_HORAS_DIA_EXTENDIDO} horas al día",
            }
        if total_dia > MAX_HORAS_DIA and horas_dia <= MAX_HORAS_DIA:
            dias_extendidos = sum(
                1
                for dia, horas in horas_por_dia.items()
                if dia != str(fecha) and horas > MAX_HORAS_DIA
            )
            if dias_extendidos >= MAX_DIAS_EXTENDIDOS:
                return {
                    "status": "error",
                    "message": (
                        f"El docente solo puede tener {MAX_DIAS_EXTENDIDOS} días de "
                        f"{MAX_HORAS_DIA_EXTENDIDO} horas; el resto máximo {MAX_HORAS_DIA} horas diarias"
                    ),
                }

        horas_semana = sum(horas_por_dia.values())
        if horas_semana + horas_nuevas > MAX_HORAS_SEMANA:
            return {
                "status": "error",
                "message": f"El docente no puede agendar más de {MAX_HORAS_SEMANA} horas semanales",
            }
        return None

    def _lunes_de(self, fecha):
        dia = datetime.strptime(str(fecha), "%Y-%m-%d").date()
        return dia - timedelta(days=dia.weekday())

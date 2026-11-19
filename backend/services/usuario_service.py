import logging
import os

from interfaces.email_validator import IEmailValidator
from interfaces.password_hasher import IPasswordHasher
from interfaces.usuario_repository import IUsuarioRepository
from services.mailer import enviar_correo, smtp_configurado
from services.password_policy import validar_password
from services.password_reset import (
    decodificar_token_restablecimiento,
)
from services.reset_pin_store import generar_pin, guardar_pin, verificar_y_consumir_pin
from superadmin_ancla import ROL_SUPERADMIN, SUPERADMIN_ANCLA

logger = logging.getLogger(__name__)

ROLES_VALIDOS = {1, 2, 3}


class UsuarioService:
    def __init__(self, repository: IUsuarioRepository, password_hasher: IPasswordHasher, email_validator: IEmailValidator):
        self._repository = repository
        self._password_hasher = password_hasher
        self._email_validator = email_validator

    def crear_usuario(self, data):
        error = self._email_validator.validar(data.get("email", ""))
        if error:
            return error
        error_clave = validar_password(data.get("password"))
        if error_clave:
            return error_clave
        try:
            id_rol = int(data["id_rol"])
        except (TypeError, ValueError):
            return {"status": "error", "message": "El rol no es válido"}
        if id_rol == ROL_SUPERADMIN:
            solicitante = (data.get("solicitante_email") or "").lower()
            if solicitante != SUPERADMIN_ANCLA:
                return {
                    "status": "error",
                    "message": "Solo el superadministrador ancla puede crear otro superadministrador",
                }
        if self._repository.buscar_por_email(data.get("email", "")):
            return {"status": "error", "message": "Solo se permite un registro por correo"}

        solicitante_email = (data.get("solicitante_email") or "").lower()
        estado = "activo" if solicitante_email == SUPERADMIN_ANCLA else "pendiente"

        try:
            password_segura = self._password_hasher.hash(data["password"])
            self._repository.crear(data["nombre"], data["email"], password_segura, id_rol, estado)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        except Exception as e:
            mensaje = str(e).lower()
            if "duplicate" in mensaje or "unique" in mensaje:
                return {"status": "error", "message": "Solo se permite un registro por correo"}
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        return {"status": "ok", "message": "Cuenta creada exitosamente", "estado": estado}

    def solicitar_restablecimiento(self, email):
        correo = (email or "").strip().lower()
        mensaje_ok = (
            "Si el correo está registrado, te enviamos un código de seguridad. "
            "Revisa tu bandeja de entrada e ingresa el PIN para continuar."
        )
        if not correo:
            return {"status": "error", "message": "El correo es obligatorio"}

        try:
            usuario = self._repository.buscar_por_email(correo)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        except Exception:
            logger.exception("Error buscando usuario para restablecimiento")
            return {"status": "ok", "message": mensaje_ok, "pin_required": True}

        if not usuario:
            return {"status": "ok", "message": mensaje_ok, "pin_required": True}

        minutos = max(1, int(os.getenv("RESET_PIN_MINUTES", "15")))
        pin = generar_pin()
        guardar_pin(correo, pin)

        asunto = "Código de seguridad - SGSDev"
        texto = (
            "Recibimos una solicitud para restablecer tu contraseña en SGSDev.\n\n"
            f"Tu código de seguridad es: {pin}\n"
            f"Válido por {minutos} minutos.\n\n"
            "Si no solicitaste este cambio, ignora este mensaje."
        )
        html = (
            "<p>Recibimos una solicitud para restablecer tu contraseña en <strong>SGSDev</strong>.</p>"
            f"<p>Tu código de seguridad es: <strong style=\"font-size:1.4em;letter-spacing:0.15em\">{pin}</strong></p>"
            f"<p>Válido por {minutos} minutos. Si no solicitaste este cambio, ignora este mensaje.</p>"
        )

        if smtp_configurado():
            envio = enviar_correo(correo, asunto, texto, html=html)
            if not envio.get("ok"):
                logger.error("Fallo SMTP al restablecer %s: %s", correo, envio.get("message"))
                return {
                    "status": "error",
                    "message": "No se pudo enviar el código de seguridad. Intenta más tarde.",
                }
        else:
            logger.warning(
                "SMTP no configurado. PIN de restablecimiento para %s (solo logs): %s",
                correo,
                pin,
            )

        return {"status": "ok", "message": mensaje_ok, "pin_required": True}

    def restablecer_password(self, token=None, nueva_password=None, email=None, pin=None):
        correo = None
        if email and pin:
            correo = (email or "").strip().lower()
            if not verificar_y_consumir_pin(correo, pin):
                return {
                    "status": "error",
                    "message": "El código de seguridad es inválido o ya expiró",
                }
        else:
            correo = decodificar_token_restablecimiento(token or "")
            if not correo:
                return {
                    "status": "error",
                    "message": "El código o enlace de restablecimiento es inválido o ya expiró",
                }

        error_clave = validar_password(nueva_password)
        if error_clave:
            return error_clave
        usuario = self._repository.buscar_por_email(correo)
        if not usuario:
            return {"status": "error", "message": "No hay una cuenta registrada con ese correo"}
        try:
            password_segura = self._password_hasher.hash(nueva_password)
            self._repository.actualizar_password(correo, password_segura)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        except Exception:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        return {"status": "ok", "message": "Contraseña restablecida. Ya puedes iniciar sesión"}

    def listar_usuarios(self):
        try:
            return {"status": "ok", "data": [self._publico(u) for u in self._repository.listar()]}
        except ConnectionError:
            return {
                "status": "error",
                "message": "No se pudo completar la operación. Intenta de nuevo.",
                "data": [],
            }

    def cambiar_rol(self, id_usuario, id_rol, solicitante_email):
        solicitante = self._exigir_superadmin(solicitante_email)
        if isinstance(solicitante, dict) and solicitante.get("status") == "error":
            return solicitante
        try:
            nuevo_rol = int(id_rol)
        except (TypeError, ValueError):
            return {"status": "error", "message": "El rol no es válido"}
        if nuevo_rol not in ROLES_VALIDOS:
            return {"status": "error", "message": "El rol no es válido"}
        objetivo = self._repository.buscar_por_id(id_usuario)
        if not objetivo:
            return {"status": "error", "message": "La cuenta no existe"}
        if self._es_ancla(objetivo):
            return {"status": "error", "message": "El superadministrador ancla no se puede modificar"}
        if nuevo_rol == ROL_SUPERADMIN and not self._es_ancla(solicitante):
            return {
                "status": "error",
                "message": "Solo el superadministrador ancla puede asignar el rol de superadministrador",
            }
        try:
            actualizado = self._repository.actualizar_rol(id_usuario, nuevo_rol)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        except Exception:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        if not actualizado:
            return {"status": "error", "message": "La cuenta ya no existe"}
        return {"status": "ok", "message": "Rol actualizado"}

    def eliminar_cuenta(self, id_usuario, solicitante_email):
        solicitante = self._exigir_superadmin(solicitante_email)
        if isinstance(solicitante, dict) and solicitante.get("status") == "error":
            return solicitante
        objetivo = self._repository.buscar_por_id(id_usuario)
        if not objetivo:
            return {"status": "error", "message": "La cuenta no existe"}
        if self._es_ancla(objetivo):
            return {"status": "error", "message": "El superadministrador ancla no se puede eliminar"}
        if (objetivo.get("email") or "").lower() == (solicitante.get("email") or "").lower():
            return {"status": "error", "message": "No puedes eliminar tu propia cuenta"}
        try:
            eliminado = self._repository.eliminar(id_usuario)
        except ConnectionError:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        except Exception:
            return {"status": "error", "message": "No se pudo completar la operación. Intenta de nuevo."}
        if not eliminado:
            return {"status": "error", "message": "La cuenta ya no existe"}
        return {"status": "ok", "message": "Cuenta eliminada"}

    def _exigir_superadmin(self, email):
        if not email:
            return {"status": "error", "message": "Solo un superadministrador puede gestionar cuentas"}
        solicitante = self._repository.buscar_por_email(email)
        if not solicitante or int(solicitante.get("id_rol") or 0) != ROL_SUPERADMIN:
            return {"status": "error", "message": "Solo un superadministrador puede gestionar cuentas"}
        return solicitante

    def _es_ancla(self, usuario):
        return (usuario.get("email") or "").lower() == SUPERADMIN_ANCLA

    def _publico(self, usuario):
        return {
            "id_usuario": usuario["id_usuario"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
            "id_rol": usuario["id_rol"],
            "estado": usuario.get("estado", "activo"),
        }

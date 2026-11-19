import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def smtp_configurado():
    return bool((os.getenv("SMTP_HOST") or "").strip())


def enviar_correo(destinatario, asunto, texto, html=None):
    """
    Envía correo por SMTP si está configurado.
    Retorna {"ok": True} o {"ok": False, "message": "..."}.
    """
    host = (os.getenv("SMTP_HOST") or "").strip()
    if not host:
        return {"ok": False, "message": "SMTP no configurado"}

    port = int(os.getenv("SMTP_PORT", "587"))
    user = (os.getenv("SMTP_USER") or "").strip()
    password = os.getenv("SMTP_PASSWORD") or ""
    remitente = (os.getenv("SMTP_FROM") or user or "noreply@sgsdev.local").strip()
    use_tls = (os.getenv("SMTP_TLS", "1") or "1").strip() not in {"0", "false", "False"}

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if user:
                server.login(user, password)
            server.send_message(mensaje)
        logger.info("Correo enviado a %s (%s)", destinatario, asunto)
        return {"ok": True}
    except Exception as error:
        logger.exception("No se pudo enviar correo a %s", destinatario)
        return {"ok": False, "message": str(error)}

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class EmailNotConfiguredError(RuntimeError):
    """Se intentó enviar un email sin SMTP_USER / SMTP_PASSWORD configurados."""


def _build_message(
    to_emails: list[str],
    subject: str,
    body: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


async def _send(msg: EmailMessage) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        raise EmailNotConfiguredError(
            "SMTP_USER / SMTP_PASSWORD no configurados en el entorno"
        )
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )


async def send_report_email(
    to_emails: list[str],
    report_title: str,
    period_label: str,
    attachment_bytes: bytes,
    attachment_filename: str,
) -> None:
    """Envía el reporte Excel adjunto a los destinatarios vía Gmail SMTP (STARTTLS)."""
    subject = f"[Reporte CDR] {report_title} — {period_label}"
    body = (
        f"Adjunto el reporte '{report_title}' correspondiente al período: {period_label}.\n\n"
        "Este es un envío automático del sistema de xDRCompress.\n"
        "No responda a este correo."
    )
    msg = _build_message(to_emails, subject, body)
    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype=_XLSX_MIME.split("/", 1)[1],
        filename=attachment_filename,
    )

    logger.info("Enviando reporte '%s' a %s (%s)", report_title, to_emails, attachment_filename)
    await _send(msg)
    logger.info("Email enviado OK a %s", to_emails)


async def send_error_email(
    to_emails: list[str],
    report_title: str,
    period_label: str,
    error_traceback: str,
) -> None:
    """Notifica un fallo en la generación del reporte (regla 6 del spec)."""
    subject = f"[Reporte CDR][ERROR] {report_title} — {period_label}"
    body = (
        f"Ocurrió un error al generar el reporte '{report_title}' "
        f"para el período: {period_label}.\n\n"
        "Detalle técnico:\n"
        f"{error_traceback}\n\n"
        "Este es un envío automático del sistema de Reportes CDR."
    )
    msg = _build_message(to_emails, subject, body)

    logger.info("Enviando email de ERROR de '%s' a %s", report_title, to_emails)
    await _send(msg)
    logger.info("Email de error enviado OK a %s", to_emails)

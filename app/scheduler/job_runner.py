import asyncio
import json
import logging
import traceback
from datetime import datetime

from app.db.session import _make_client
from app.reports.registry import REGISTRY
from app.scheduler.database import AsyncSessionLocal
from app.scheduler.email_service import send_error_email, send_report_email
from app.scheduler.models import ScheduledReport
from app.scheduler.periods import compute_period

logger = logging.getLogger(__name__)


def _generate_excel_bytes(report_id: str, date_from, date_to) -> bytes:
    """Trabajo bloqueante (ClickHouse + openpyxl). Se corre en un thread aparte
    para no bloquear el event loop. Llama directo a la función Python del
    reporte — NO hace HTTP interno (regla 2 del spec)."""
    client = _make_client()
    try:
        report = REGISTRY[report_id](client)
        buffer = report.generate_excel(date_from, date_to)
        return buffer.getvalue()
    finally:
        client.close()


async def run_scheduled_report(schedule_id: str) -> None:
    """Punto de entrada del job: carga el schedule, genera el Excel y lo envía.

    Cualquier error se loggea y se notifica por email al destinatario (regla 6).
    """
    async with AsyncSessionLocal() as session:
        row = await session.get(ScheduledReport, schedule_id)

    if row is None:
        logger.error("Job abortado: schedule %s no existe en DB", schedule_id)
        return

    emails = json.loads(row.emails)
    report_cls = REGISTRY.get(row.report_id)
    report_title = report_cls.name if report_cls else row.report_id
    period = compute_period(row.frequency)

    logger.info(
        "Ejecutando job schedule=%s report=%s período=%s",
        schedule_id, row.report_id, period.label,
    )

    try:
        excel_bytes = await asyncio.to_thread(
            _generate_excel_bytes, row.report_id, period.date_from, period.date_to
        )
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{row.report_id}_{row.frequency}_{period.token}_{timestamp}.xlsx"

        await send_report_email(
            to_emails=emails,
            report_title=report_title,
            period_label=period.label,
            attachment_bytes=excel_bytes,
            attachment_filename=filename,
        )
        logger.info("Job OK schedule=%s -> %s (%d bytes)", schedule_id, filename, len(excel_bytes))
    except Exception:
        tb = traceback.format_exc()
        logger.error("Job FALLÓ schedule=%s report=%s\n%s", schedule_id, row.report_id, tb)
        try:
            await send_error_email(emails, report_title, period.label, tb)
        except Exception:
            logger.exception("Además falló el envío del email de error schedule=%s", schedule_id)

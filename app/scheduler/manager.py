import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.scheduler.database import AsyncSessionLocal
from app.scheduler.job_runner import run_scheduled_report
from app.scheduler.models import ScheduledReport

logger = logging.getLogger(__name__)

# El contenedor corre en UTC; fijamos la tz como STRING (APScheduler la resuelve
# internamente con pytz). Pasar un objeto zoneinfo.ZoneInfo NO es portable: en
# Linux el CronTrigger terminaba ignorándola y quedaba en UTC. Además la tz se
# pasa explícita a cada CronTrigger para no depender de que la herede del scheduler.
_TZ = settings.scheduler_timezone
scheduler = AsyncIOScheduler(timezone=_TZ)


def _build_trigger(row: ScheduledReport) -> CronTrigger:
    """Mapea frequency -> CronTrigger. APScheduler usa day_of_week 0-6 = lun-dom,
    igual que el spec. La tz se fija explícita en cada trigger."""
    if row.frequency == "daily":
        return CronTrigger(hour=row.hour, minute=row.minute, timezone=_TZ)
    if row.frequency == "weekly":
        return CronTrigger(
            day_of_week=row.day_of_week, hour=row.hour, minute=row.minute, timezone=_TZ
        )
    if row.frequency == "monthly":
        return CronTrigger(
            day=row.day_of_month, hour=row.hour, minute=row.minute, timezone=_TZ
        )
    raise ValueError(f"Frecuencia inválida: {row.frequency}")


def schedule_job(row: ScheduledReport) -> None:
    """Agrega o reemplaza el job en APScheduler (idempotente, regla 7)."""
    scheduler.add_job(
        run_scheduled_report,
        trigger=_build_trigger(row),
        args=[row.id],
        id=row.id,
        replace_existing=True,
    )
    logger.info(
        "Job programado id=%s freq=%s %02d:%02d", row.id, row.frequency, row.hour, row.minute
    )


def unschedule_job(schedule_id: str) -> None:
    if scheduler.get_job(schedule_id):
        scheduler.remove_job(schedule_id)
        logger.info("Job removido id=%s", schedule_id)


def sync_job(row: ScheduledReport) -> None:
    """Refleja el estado `active` del schedule en APScheduler."""
    if row.active:
        schedule_job(row)
    else:
        unschedule_job(row.id)


def trigger_now(schedule_id: str) -> None:
    """Encola una ejecución inmediata (run-now), independiente del trigger cron."""
    now = datetime.now(scheduler.timezone)
    scheduler.add_job(
        run_scheduled_report,
        trigger="date",
        run_date=now,
        args=[schedule_id],
        id=f"run-now:{schedule_id}:{now:%Y%m%d%H%M%S%f}",
    )
    logger.info("Run-now encolado id=%s", schedule_id)


async def load_schedules() -> None:
    """Carga todos los schedules activos de SQLite al arrancar (regla 4)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScheduledReport).where(ScheduledReport.active == 1)
        )
        rows = result.scalars().all()
    for row in rows:
        schedule_job(row)
    logger.info("Cargados %d schedules activos en APScheduler", len(rows))


def start() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler iniciado")


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler detenido")

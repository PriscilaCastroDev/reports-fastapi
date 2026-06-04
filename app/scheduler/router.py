import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.scheduler import manager
from app.scheduler.database import get_session
from app.scheduler.models import ScheduledReport
from app.scheduler.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_response(row: ScheduledReport) -> ScheduleResponse:
    return ScheduleResponse(
        id=row.id,
        report_id=row.report_id,
        emails=json.loads(row.emails),
        frequency=row.frequency,
        hour=row.hour,
        minute=row.minute,
        day_of_week=row.day_of_week,
        day_of_month=row.day_of_month,
        active=bool(row.active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _get_or_404(session: AsyncSession, schedule_id: str) -> ScheduledReport:
    row = await session.get(ScheduledReport, schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' no encontrado")
    return row


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear schedule",
)
async def create_schedule(
    payload: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    now = _now_iso()
    row = ScheduledReport(
        id=str(uuid.uuid4()),
        report_id=payload.report_id,
        emails=json.dumps(payload.emails),
        frequency=payload.frequency.value,
        hour=payload.hour,
        minute=payload.minute,
        day_of_week=payload.day_of_week,
        day_of_month=payload.day_of_month,
        active=1,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    manager.schedule_job(row)
    logger.info("Schedule creado id=%s report=%s freq=%s", row.id, row.report_id, row.frequency)
    return _to_response(row)


@router.get(
    "",
    response_model=list[ScheduleResponse],
    summary="Listar schedules",
)
async def list_schedules(
    report_id: str | None = Query(None, description="Filtrar por report_id"),
    session: AsyncSession = Depends(get_session),
) -> list[ScheduleResponse]:
    stmt = select(ScheduledReport)
    if report_id:
        stmt = stmt.where(ScheduledReport.report_id == report_id)
    stmt = stmt.order_by(ScheduledReport.created_at.desc())
    result = await session.execute(stmt)
    return [_to_response(r) for r in result.scalars().all()]


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Obtener schedule por ID",
)
async def get_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    row = await _get_or_404(session, schedule_id)
    return _to_response(row)


@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Actualizar schedule",
)
async def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    row = await _get_or_404(session, schedule_id)
    row.report_id = payload.report_id
    row.emails = json.dumps(payload.emails)
    row.frequency = payload.frequency.value
    row.hour = payload.hour
    row.minute = payload.minute
    row.day_of_week = payload.day_of_week
    row.day_of_month = payload.day_of_month
    row.updated_at = _now_iso()
    await session.commit()
    await session.refresh(row)
    manager.sync_job(row)  # reprograma (o remueve si está pausado)
    logger.info("Schedule actualizado id=%s", row.id)
    return _to_response(row)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar schedule",
)
async def delete_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    row = await _get_or_404(session, schedule_id)
    await session.delete(row)
    await session.commit()
    manager.unschedule_job(schedule_id)
    logger.info("Schedule eliminado id=%s", schedule_id)


@router.post(
    "/{schedule_id}/toggle",
    response_model=ScheduleResponse,
    summary="Activar/pausar schedule",
)
async def toggle_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    row = await _get_or_404(session, schedule_id)
    row.active = 0 if row.active else 1
    row.updated_at = _now_iso()
    await session.commit()
    await session.refresh(row)
    manager.sync_job(row)  # agrega o remueve el job según el nuevo estado
    logger.info("Schedule toggle id=%s active=%s", row.id, row.active)
    return _to_response(row)


@router.post(
    "/{schedule_id}/run-now",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ejecutar el reporte inmediatamente (testing)",
)
async def run_now(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await _get_or_404(session, schedule_id)
    manager.trigger_now(schedule_id)
    return {"status": "accepted", "schedule_id": schedule_id}

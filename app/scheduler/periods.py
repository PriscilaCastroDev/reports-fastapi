"""Cálculo del período a reportar según la frecuencia del schedule.

Regla del spec:
  - daily   -> el día de ayer
  - weekly  -> la semana anterior (lun-dom completa)
  - monthly -> el mes anterior

Devuelve el rango [date_from, date_to) (to exclusivo, igual que get_date_range),
un `token` compacto para el nombre de archivo y un `label` legible para el email.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings

_MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


@dataclass(frozen=True)
class PeriodInfo:
    date_from: datetime
    date_to: datetime
    token: str   # compacto, para filename (sin espacios)
    label: str   # legible, para subject/cuerpo del email


def _week_of_month(week_start: date) -> int:
    """Número de semana (1-based) dentro del mes del lunes `week_start`,
    consistente con app.services.date_range.get_date_range."""
    first_of_month = date(week_start.year, week_start.month, 1)
    first_monday = first_of_month - timedelta(days=first_of_month.weekday())
    return ((week_start - first_monday).days // 7) + 1


def compute_period(frequency: str, today: date | None = None) -> PeriodInfo:
    # "Hoy" en la tz del scheduler, no en UTC del contenedor (cerca de
    # medianoche el período calculado debe coincidir con la hora local).
    today = today or datetime.now(ZoneInfo(settings.scheduler_timezone)).date()

    if frequency == "daily":
        yesterday = today - timedelta(days=1)
        start = datetime(yesterday.year, yesterday.month, yesterday.day)
        return PeriodInfo(
            date_from=start,
            date_to=start + timedelta(days=1),
            token=yesterday.strftime("%Y-%m-%d"),
            label=f"Diario {yesterday.strftime('%Y-%m-%d')}",
        )

    if frequency == "weekly":
        this_monday = today - timedelta(days=today.weekday())
        # --- PRUEBA: semana EN CURSO -----------------------------------------
        ref_monday = this_monday
        # --- NORMAL: semana anterior completa (revertir descomentando) --------
        # ref_monday = this_monday - timedelta(days=7)
        # ---------------------------------------------------------------------
        start = datetime(ref_monday.year, ref_monday.month, ref_monday.day)
        week = _week_of_month(ref_monday)
        return PeriodInfo(
            date_from=start,
            date_to=start + timedelta(days=7),
            token=f"{ref_monday.year}-{ref_monday.month:02d}-w{week}",
            label=f"Semana {week} - {_MONTHS_ES[ref_monday.month - 1]} {ref_monday.year}",
        )

    if frequency == "monthly":
        # --- PRUEBA: mes EN CURSO --------------------------------------------
        year, month = today.year, today.month
        # --- NORMAL: mes anterior completo (revertir descomentando) ----------
        # first_this_month = date(today.year, today.month, 1)
        # last_month_day = first_this_month - timedelta(days=1)
        # year, month = last_month_day.year, last_month_day.month
        # ---------------------------------------------------------------------
        start = datetime(year, month, 1)
        next_month = datetime(year + (month // 12), (month % 12) + 1, 1)
        return PeriodInfo(
            date_from=start,
            date_to=next_month,
            token=f"{year}-{month:02d}",
            label=f"{_MONTHS_ES[month - 1]} {year}",
        )

    raise ValueError(f"Frecuencia inválida: {frequency}")

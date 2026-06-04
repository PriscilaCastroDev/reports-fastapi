import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.reports.registry import REGISTRY

# Fuente única de verdad: los mismos reportes del catálogo de descargas manuales.
VALID_REPORT_IDS: frozenset[str] = frozenset(REGISTRY.keys())

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Frequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class ScheduleBase(BaseModel):
    report_id: str = Field(..., description="Slug de uno de los 6 reportes disponibles")
    emails: list[str] = Field(..., min_length=1, description="Destinatarios del reporte")
    frequency: Frequency
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    day_of_week: int | None = Field(None, ge=0, le=6, description="0=lun … 6=dom, solo weekly")
    day_of_month: int | None = Field(None, ge=1, le=28, description="1-28, solo monthly")

    @field_validator("report_id")
    @classmethod
    def _validate_report_id(cls, v: str) -> str:
        if v not in VALID_REPORT_IDS:
            raise ValueError(
                f"report_id inválido: '{v}'. Válidos: {sorted(VALID_REPORT_IDS)}"
            )
        return v

    @field_validator("emails")
    @classmethod
    def _validate_emails(cls, v: list[str]) -> list[str]:
        cleaned = [e.strip() for e in v if e.strip()]
        if not cleaned:
            raise ValueError("Se requiere al menos un email")
        for email in cleaned:
            if not _EMAIL_RE.match(email):
                raise ValueError(f"Email inválido: '{email}'")
        return cleaned

    @model_validator(mode="after")
    def _validate_frequency_fields(self) -> "ScheduleBase":
        if self.frequency == Frequency.weekly and self.day_of_week is None:
            raise ValueError("'day_of_week' es requerido cuando frequency='weekly'")
        if self.frequency == Frequency.monthly and self.day_of_month is None:
            raise ValueError("'day_of_month' es requerido cuando frequency='monthly'")
        # Normaliza: ignora campos que no aplican a la frecuencia elegida
        if self.frequency != Frequency.weekly:
            self.day_of_week = None
        if self.frequency != Frequency.monthly:
            self.day_of_month = None
        return self


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(ScheduleBase):
    pass


class ScheduleResponse(BaseModel):
    id: str
    report_id: str
    emails: list[str]
    frequency: Frequency
    hour: int
    minute: int
    day_of_week: int | None
    day_of_month: int | None
    active: bool
    created_at: str
    updated_at: str

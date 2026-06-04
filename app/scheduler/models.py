from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScheduledReport(Base):
    """Configuración persistida de un envío automático de reporte por email.

    Los emails se guardan como JSON string: '["a@b.com", "c@d.com"]'.
    `active` y los flags se guardan como INTEGER (SQLite no tiene boolean nativo).
    """

    __tablename__ = "scheduled_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID v4
    report_id: Mapped[str] = mapped_column(String, nullable=False)
    emails: Mapped[str] = mapped_column(String, nullable=False)  # JSON array string
    frequency: Mapped[str] = mapped_column(String, nullable=False)  # daily|weekly|monthly
    hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-23
    minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-59
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-6, solo weekly
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-28, solo monthly
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1=activo, 0=pausado
    created_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO 8601
    updated_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO 8601

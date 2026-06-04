import logging

from clickhouse_connect.driver.client import Client
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db.session import get_db
from app.reports.registry import REGISTRY
from app.schemas.reports import ErrorDetail, ReportListResponse, ReportMeta
from app.services.date_range import get_date_range, get_period_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_DESCRIPTIONS: dict[str, str] = {
    "duplicate-cdrs": "Registros de la tabla xdr.cdrs_errors con error_description = 'REGISTRO_DUPLICADO'.",
    "volume-by-record-type": "Volumen de CDRs agrupado por record_type (1=Voz, 2=SMS, 3=Datos) con duración total.",
    "dropped-calls": "Llamadas con duration = 0, indicando llamadas caídas o no conectadas.",
    "suspicious-imsis": "IMSIs asociados a más de un IMEI en el período — posible fraude o clonación de SIM.",
    "cdr-errors": "Errores de CDRs (excluye duplicados). Hoja 'Detalle' con todos los registros; hoja 'Resumen' agrupado por tipo de error con conteo y porcentaje.",
    "duplicate-files": "Archivos duplicados detectados. Hoja 'Detalle' ordenada por detected_at DESC; hoja 'Resumen' agrupado por source_component con conteo y porcentaje.",
}


@router.get(
    "",
    response_model=ReportListResponse,
    summary="Listar reportes disponibles",
    description="Retorna el catálogo completo de reportes que pueden descargarse.",
)
def list_reports() -> ReportListResponse:
    reports = [
        ReportMeta(
            id=slug,
            name=cls.name,
            description=_DESCRIPTIONS[slug],
            filename_prefix=cls.filename_prefix,
        )
        for slug, cls in REGISTRY.items()
    ]
    return ReportListResponse(reports=reports)


@router.get(
    "/{report_name}",
    summary="Descargar reporte en Excel",
    description=(
        "Genera y descarga el reporte especificado en formato `.xlsx` para el período indicado.\n\n"
        "**Combinaciones válidas de parámetros según granularidad:**\n\n"
        "- `DAY` → `date` (YYYY-MM-DD)\n"
        "- `WEEK` → `year` + `month` (entero) + `week` (número de semana del mes, 1-based)\n"
        "- `MONTH` → `month` (YYYY-MM)\n\n"
        "El archivo descargado tiene el nombre `{prefix}_{periodo}.xlsx`."
    ),
    response_description="Archivo Excel (.xlsx) con los datos del reporte.",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Archivo Excel generado exitosamente.",
        },
        400: {"model": ErrorDetail, "description": "Parámetros de fecha inválidos o faltantes."},
        404: {"model": ErrorDetail, "description": "Nombre de reporte no existe en el catálogo."},
        500: {"model": ErrorDetail, "description": "Error interno al generar el reporte."},
    },
)
def download_report(
    report_name: str,
    granularity: str = Query(
        ...,
        pattern="^(DAY|WEEK|MONTH)$",
        description="Granularidad temporal del reporte.",
        examples={
            "day": {"summary": "Por día", "value": "DAY"},
            "week": {"summary": "Por semana", "value": "WEEK"},
            "month": {"summary": "Por mes", "value": "MONTH"},
        },
    ),
    date: str | None = Query(
        None,
        description="Fecha exacta. **Requerido cuando `granularity=DAY`.**",
        example="2024-05-15",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    year: int | None = Query(
        None,
        description="Año (4 dígitos). **Requerido cuando `granularity=WEEK`.**",
        example=2024,
        ge=2000,
        le=2099,
    ),
    month: str | None = Query(
        None,
        description=(
            "Mes como entero (`5`) cuando `granularity=WEEK`, "
            "o como `YYYY-MM` (`2024-05`) cuando `granularity=MONTH`."
        ),
        example="2024-05",
    ),
    week: int | None = Query(
        None,
        description="Número de semana dentro del mes (1-based). **Requerido cuando `granularity=WEEK`.**",
        example=2,
        ge=1,
        le=6,
    ),
    db: Client = Depends(get_db),
) -> StreamingResponse:
    if report_name not in REGISTRY:
        raise HTTPException(status_code=404, detail=f"Reporte '{report_name}' no encontrado")

    try:
        value = _build_value(granularity, date, year, month, week)
        date_from, date_to = get_date_range(granularity, value)
        period_label = get_period_label(granularity, value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    report = REGISTRY[report_name](db)
    filename = report.build_filename(period_label)

    logger.info("Generating report=%s period=%s", report_name, period_label)

    try:
        buffer = report.generate_excel(date_from, date_to)
    except Exception:
        logger.exception("Error generating report=%s", report_name)
        raise HTTPException(status_code=500, detail="Error al generar el reporte")

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_value(
    granularity: str,
    date: str | None,
    year: int | None,
    month: str | None,
    week: int | None,
) -> dict:
    if granularity == "DAY":
        if not date:
            raise ValueError("Se requiere el parámetro 'date' (formato YYYY-MM-DD)")
        return {"date": date}

    if granularity == "WEEK":
        if not (year and month and week):
            raise ValueError("Se requieren 'year', 'month' y 'week' para granularidad WEEK")
        try:
            return {"year": year, "month": int(month), "week": week}
        except (ValueError, TypeError):
            raise ValueError("El parámetro 'month' para WEEK debe ser un entero (ej: 5)")

    if granularity == "MONTH":
        if not month:
            raise ValueError("Se requiere el parámetro 'month' (formato YYYY-MM)")
        return {"month": month}

    raise ValueError(f"Granularidad inválida: {granularity}")

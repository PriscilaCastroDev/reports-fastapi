import logging

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.routers import reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DESCRIPTION = """
## CDR Reports API

Backend de reportes operativos sobre **CDRs (Call Detail Records)** de telefonía.
Genera archivos `.xlsx` descargables bajo demanda a partir de datos en ClickHouse.

### Reportes disponibles

| Slug | Nombre | Descripción |
|------|--------|-------------|
| `volume-by-record-type` | Volumen por Tipo de Registro | CDRs agrupados por record_type (Voz / SMS / Datos) |
| `dropped-calls` | Llamadas Caídas | Llamadas con `duration = 0` |
| `suspicious-imsis` | IMSIs/IMEIs Sospechosos | IMSIs asociados a más de un IMEI |
| `duplicate-cdrs` | CDRs Duplicados | Registros con `error_description = 'REGISTRO_DUPLICADO'` |

### Granularidades soportadas

| Valor | Parámetros requeridos | Ejemplo |
|-------|-----------------------|---------|
| `DAY` | `date` (YYYY-MM-DD) | `?granularity=DAY&date=2024-05-01` |
| `WEEK` | `year`, `month`, `week` | `?granularity=WEEK&year=2024&month=5&week=2` |
| `MONTH` | `month` (YYYY-MM) | `?granularity=MONTH&month=2024-05` |
"""

_TAGS_METADATA = [
    {
        "name": "reports",
        "description": "Endpoints para descargar reportes en formato Excel (.xlsx).",
    },
    {
        "name": "health",
        "description": "Verificación del estado del servicio.",
    },
]

app = FastAPI(
    title="CDR Reports API",
    description=_DESCRIPTION,
    version="0.1.0",
    openapi_tags=_TAGS_METADATA,
    contact={
        "name": "TXM Global — Equipo de Desarrollo",
        "email": "pcastro@txmglobal.com",
    },
    license_info={
        "name": "Privado — TXM Global",
    },
)

app.include_router(reports.router)


@app.get("/health", tags=["health"], summary="Health check")
def health_check() -> dict[str, str]:
    """Retorna `{"status": "ok"}` si el servicio está en línea."""
    return {"status": "ok"}

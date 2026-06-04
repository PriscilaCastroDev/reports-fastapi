import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.routers import reports
from app.scheduler import manager
from app.scheduler import router as schedules
from app.scheduler.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # Crea tablas SQLite si no existen
    logger.info("SQLite inicializado en %s", settings.sqlite_path)
    await manager.load_schedules()  # Re-registra schedules activos (regla 4)
    manager.start()
    yield
    manager.shutdown()

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
| `cdr-errors` | Errores por CDR | Errores de ingesta (excluye duplicados) — 2 hojas: Detalle + Resumen |
| `duplicate-files` | Archivos Duplicados | Archivos rechazados por duplicidad — 2 hojas: Detalle + Resumen |

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
        "name": "schedules",
        "description": "CRUD de reportes programados (envío automático por email).",
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
    lifespan=lifespan,
    openapi_tags=_TAGS_METADATA,
    contact={
        "name": "TXM Global — Equipo de Desarrollo",
        "email": "pcastro@txmglobal.com",
    },
    license_info={
        "name": "Privado — TXM Global",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(schedules.router)


@app.get("/health", tags=["health"], summary="Health check")
def health_check() -> dict[str, str]:
    """Retorna `{"status": "ok"}` si el servicio está en línea."""
    return {"status": "ok"}

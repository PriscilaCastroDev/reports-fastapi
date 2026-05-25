# CDR Reports Backend

API REST para generación de reportes operativos sobre CDRs en formato Excel (.xlsx).

## Stack

- Python 3.12
- FastAPI + Uvicorn
- clickhouse-connect (ClickHouse)
- openpyxl

## Setup

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con los datos reales de la BD

# 4. Levantar el servidor
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 4002 --reload
```

## Docker

```bash
docker build -t cdr-reports:latest .
docker run -d --name cdr-reports -p 4002:4002 --env-file .env cdr-reports:latest
```

## Endpoints disponibles

| Método | Path                                    | Descripción                      |
| ------ | --------------------------------------- | -------------------------------- |
| GET    | `/health`                               | Healthcheck                      |
| GET    | `/api/v1/reports`                       | Catálogo de reportes disponibles |
| GET    | `/api/v1/reports/volume-by-record-type` | Volumen por tipo de registro     |
| GET    | `/api/v1/reports/dropped-calls`         | Llamadas caídas                  |
| GET    | `/api/v1/reports/suspicious-imsis`      | IMSIs/IMEIs sospechosos          |
| GET    | `/api/v1/reports/duplicate-cdrs`        | CDRs duplicados                  |
| GET    | `/docs`                                 | Swagger UI (documentación)       |

## Parámetros de periodo

| Granularidad | Parámetros requeridos         | Ejemplo                                      |
| ------------ | ----------------------------- | -------------------------------------------- |
| `DAY`        | `date=YYYY-MM-DD`             | `?granularity=DAY&date=2026-05-21`           |
| `WEEK`       | `year`, `month` (int), `week` | `?granularity=WEEK&year=2026&month=5&week=3` |
| `MONTH`      | `month=YYYY-MM`               | `?granularity=MONTH&month=2026-05`           |

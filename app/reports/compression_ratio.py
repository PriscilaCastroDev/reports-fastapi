from datetime import datetime
from io import BytesIO

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport
from app.services.excel_builder import build_excel_multisheet

# Umbral de "baja compresión": compress_percent es % de reducción (más alto = mejor).
_LOW_COMPRESSION_THRESHOLD = 85

_SUMMARY_COLUMNS: list[tuple[str, str]] = [
    ("Métrica", "metrica"),
    ("Valor", "valor"),
]


class CompressionRatioReport(BaseReport):
    name = "Ratio de Compresión"
    filename_prefix = "compresion_ratio"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        # Una sola query; los KPIs se agregan en Python. Se traen original_size /
        # parquet_size en bytes crudos (no GB) para no perder precisión y evitar
        # el underflow de UInt64 que tendría sum(original_size - parquet_size) en SQL.
        sql = """
            SELECT
                filename,
                max(eventTime)        AS eventTime,
                max(original_size)    AS original_size,
                max(parquet_size)     AS parquet_size,
                max(compress_percent) AS compress_percent
            FROM xdr.cold_metrics
            WHERE eventTime >= {from_dt:DateTime}
              AND eventTime < {to_dt:DateTime}
              AND compress_percent > 0
            GROUP BY filename
            ORDER BY eventTime DESC
        """
        result = self.db.query(
            sql,
            parameters={"from_dt": date_from, "to_dt": date_to},
        )
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def columns(self) -> list[tuple[str, str]]:
        return [
            ("Filename", "filename"),
            ("Event Time", "eventTime"),
            ("Original (GB)", "original_gb"),
            ("Parquet (GB)", "parquet_gb"),
            ("Compresión (%)", "compress_percent"),
        ]

    def generate_excel(self, date_from: datetime, date_to: datetime) -> BytesIO:
        rows = self.query(date_from, date_to)
        detalle = self._build_detalle(rows)
        summary = self._build_summary(rows)
        return build_excel_multisheet([
            ("Resumen", summary, _SUMMARY_COLUMNS),
            ("Detalle", detalle, self.columns()),
        ])

    def _build_detalle(self, rows: list[dict]) -> list[dict]:
        return [
            {
                **r,
                "original_gb": round(r["original_size"] / 1e9, 2),
                "parquet_gb": round(r["parquet_size"] / 1e9, 2),
            }
            for r in rows
        ]

    def _build_summary(self, rows: list[dict]) -> list[dict]:
        total = len(rows)
        avg_compress = (
            round(sum(r["compress_percent"] for r in rows) / total, 2) if total else 0.0
        )
        # Bytes crudos (int con signo en Python) → la resta nunca hace underflow.
        ahorro_gb = round(
            sum(r["original_size"] - r["parquet_size"] for r in rows) / 1e9, 2
        )
        baja_compresion = sum(
            1 for r in rows if r["compress_percent"] < _LOW_COMPRESSION_THRESHOLD
        )
        return [
            {"metrica": "Total archivos procesados", "valor": total},
            {"metrica": "Compresión promedio (%)", "valor": avg_compress},
            {"metrica": "Ahorro total (GB)", "valor": ahorro_gb},
            {"metrica": "Archivos baja compresión (<85%)", "valor": baja_compresion},
        ]

from collections import Counter
from datetime import datetime
from io import BytesIO

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport
from app.services.excel_builder import build_excel_multisheet

_SUMMARY_COLUMNS: list[tuple[str, str]] = [
    ("Componente Origen", "source_component"),
    ("Cantidad", "cantidad"),
    ("Porcentaje (%)", "porcentaje"),
]


class DuplicateFilesReport(BaseReport):
    name = "Archivos Duplicados"
    filename_prefix = "archivos_duplicados"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = """
            SELECT filename, detected_at, source_component
            FROM xdr.duplicate_files_log
            WHERE detected_at >= {from_dt:DateTime}
              AND detected_at < {to_dt:DateTime}
            ORDER BY detected_at DESC
        """
        result = self.db.query(
            sql,
            parameters={"from_dt": date_from, "to_dt": date_to},
        )
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def columns(self) -> list[tuple[str, str]]:
        return [
            ("Nombre de Archivo", "filename"),
            ("Detectado En", "detected_at"),
            ("Componente Origen", "source_component"),
        ]

    def generate_excel(self, date_from: datetime, date_to: datetime) -> BytesIO:
        rows = self.query(date_from, date_to)
        summary = self._build_summary(rows)
        return build_excel_multisheet([
            ("Detalle", rows, self.columns()),
            ("Resumen", summary, _SUMMARY_COLUMNS),
        ])

    def _build_summary(self, rows: list[dict]) -> list[dict]:
        total = len(rows)
        counts = Counter(r["source_component"] for r in rows)
        return [
            {
                "source_component": component,
                "cantidad": count,
                "porcentaje": round(count / total * 100, 2) if total else 0.0,
            }
            for component, count in counts.most_common()
        ]

from collections import Counter
from datetime import datetime
from io import BytesIO

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport
from app.services.excel_builder import build_excel_multisheet

_SUMMARY_COLUMNS: list[tuple[str, str]] = [
    ("Descripción del Error", "error_description"),
    ("Cantidad", "cantidad"),
    ("Porcentaje (%)", "porcentaje"),
]


class CdrErrorsReport(BaseReport):
    name = "Errores por CDR"
    filename_prefix = "errores_cdr"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = """
            SELECT original_filename, error_description, raw_line, ts
            FROM xdr.cdrs_errors
            WHERE error_description != {excl:String}
              AND ts >= {from_dt:DateTime}
              AND ts < {to_dt:DateTime}
            ORDER BY ts DESC
        """
        result = self.db.query(
            sql,
            parameters={
                "excl": "REGISTRO_DUPLICADO",
                "from_dt": date_from,
                "to_dt": date_to,
            },
        )
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def columns(self) -> list[tuple[str, str]]:
        return [
            ("Archivo Original", "original_filename"),
            ("Descripción del Error", "error_description"),
            ("Línea Raw", "raw_line"),
            ("Fecha/Hora", "ts"),
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
        counts = Counter(r["error_description"] for r in rows)
        return [
            {
                "error_description": desc,
                "cantidad": count,
                "porcentaje": round(count / total * 100, 2) if total else 0.0,
            }
            for desc, count in counts.most_common()
        ]

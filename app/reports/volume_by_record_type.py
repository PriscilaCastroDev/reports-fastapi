from calendar import monthrange
from datetime import datetime

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport

_TIPO_SERVICIO: dict[int, str] = {
    1: "Voz",
    2: "SMS",
    3: "Datos",
}


def _map_tipo_servicio(record_type: int) -> str:
    return _TIPO_SERVICIO.get(record_type, "Otros")


def _cutoff_date() -> datetime:
    now = datetime.now()
    month = now.month - 6
    year = now.year
    if month <= 0:
        month += 12
        year -= 1
    max_day = monthrange(year, month)[1]
    return datetime(year, month, min(now.day, max_day))


class VolumeByRecordTypeReport(BaseReport):
    name = "Volumen por Tipo de Registro"
    filename_prefix = "distribucion_trafico"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        cutoff = _cutoff_date()

        if date_from >= cutoff:
            rows = self._query_hot(date_from, date_to)
        elif date_to <= cutoff:
            rows = self._query_cold(date_from, date_to)
        else:
            hot_rows = self._query_hot(cutoff, date_to)
            cold_rows = self._query_cold(date_from, cutoff)
            rows = self._merge(hot_rows, cold_rows)

        for row in rows:
            row["tipo_servicio"] = _map_tipo_servicio(row["record_type"])

        return sorted(rows, key=lambda r: r["total_cdrs"], reverse=True)

    def _query_hot(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = """
            SELECT
                record_type,
                COUNT() AS total_cdrs,
                SUM(duration) AS duracion_total_segundos
            FROM xdr.cdrs
            WHERE event_time >= {from_dt:DateTime}
              AND event_time < {to_dt:DateTime}
            GROUP BY record_type
        """
        result = self.db.query(sql, parameters={"from_dt": date_from, "to_dt": date_to})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def _query_cold(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = """
            SELECT
                record_type,
                COUNT() AS total_cdrs,
                SUM(duration) AS duracion_total_segundos
            FROM xdr.cdr_cold
            WHERE eventTime >= {from_dt:DateTime}
              AND eventTime < {to_dt:DateTime}
            GROUP BY record_type
        """
        result = self.db.query(sql, parameters={"from_dt": date_from, "to_dt": date_to})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def _merge(self, hot: list[dict], cold: list[dict]) -> list[dict]:
        combined: dict[int, dict] = {}
        for row in hot + cold:
            rt = row["record_type"]
            if rt not in combined:
                combined[rt] = {
                    "record_type": rt,
                    "total_cdrs": 0,
                    "duracion_total_segundos": 0,
                }
            combined[rt]["total_cdrs"] += row["total_cdrs"]
            combined[rt]["duracion_total_segundos"] += row.get("duracion_total_segundos", 0)
        return list(combined.values())

    def columns(self) -> list[tuple[str, str]]:
        return [
            ("Tipo de Registro", "record_type"),
            ("Tipo de Servicio", "tipo_servicio"),
            ("Total CDRs", "total_cdrs"),
            ("Duración Total (seg)", "duracion_total_segundos"),
        ]

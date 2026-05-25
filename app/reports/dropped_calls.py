import logging
from datetime import datetime

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport
from app.reports.volume_by_record_type import _cutoff_date

logger = logging.getLogger(__name__)

_HOT_COLS = "imsi, imei, num_a, num_b, event_time, duration, direction, cell_origin, cell_destination"
_COLD_COLS = "imsi, imei, num_a, num_b, eventTime AS event_time, duration, direction, cell_origin, cell_destination"


class DroppedCallsReport(BaseReport):
    name = "Llamadas Caídas"
    filename_prefix = "llamadas_caidas"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        cutoff = _cutoff_date()

        if date_from >= cutoff:
            rows = self._query_hot(date_from, date_to)
        elif date_to <= cutoff:
            rows = self._query_cold(date_from, date_to)
        else:
            rows = self._query_hot(cutoff, date_to) + self._query_cold(date_from, cutoff)

        return sorted(rows, key=lambda r: r["event_time"], reverse=True)

    def _query_hot(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = f"""
            SELECT {_HOT_COLS}
            FROM xdr.cdrs
            WHERE event_time >= {{from_dt:DateTime}}
              AND event_time < {{to_dt:DateTime}}
              AND duration == 0
            ORDER BY event_time DESC
        """
        result = self.db.query(sql, parameters={"from_dt": date_from, "to_dt": date_to})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def _query_cold(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = f"""
            SELECT {_COLD_COLS}
            FROM xdr.cdr_cold
            WHERE eventTime >= {{from_dt:DateTime}}
              AND eventTime < {{to_dt:DateTime}}
              AND duration == 0
            ORDER BY eventTime DESC
        """
        result = self.db.query(sql, parameters={"from_dt": date_from, "to_dt": date_to})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def columns(self) -> list[tuple[str, str]]:
        return [
            ("IMSI", "imsi"),
            ("IMEI", "imei"),
            ("Número A", "num_a"),
            ("Número B", "num_b"),
            ("Fecha/Hora Evento", "event_time"),
            ("Duración (seg)", "duration"),
            ("Dirección", "direction"),
            ("Celda Origen", "cell_origin"),
            ("Celda Destino", "cell_destination"),
        ]

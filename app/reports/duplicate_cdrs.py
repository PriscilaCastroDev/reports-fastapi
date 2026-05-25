from datetime import datetime

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport


class DuplicateCDRsReport(BaseReport):
    name = "CDRs Duplicados"
    filename_prefix = "taza_rechazo_duplicidad"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        sql = """
            SELECT *
            FROM xdr.cdrs_errors
            WHERE error_description = {error_desc:String}
              AND ts >= {from_dt:DateTime}
              AND ts < {to_dt:DateTime}
            ORDER BY ts DESC
        """
        result = self.db.query(
            sql,
            parameters={
                "error_desc": "REGISTRO_DUPLICADO",
                "from_dt": date_from,
                "to_dt": date_to,
            },
        )
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def columns(self) -> list[tuple[str, str]]:
        # Schema unknown until BD is connected — auto-detected from query results
        return []

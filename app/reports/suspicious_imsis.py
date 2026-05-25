from datetime import datetime

from clickhouse_connect.driver.client import Client

from app.reports.base import BaseReport
from app.reports.volume_by_record_type import _cutoff_date

_HOT_TABLE = "xdr.cdrs"
_HOT_TIME = "event_time"
_COLD_TABLE = "xdr.cdr_cold"
_COLD_TIME = "eventTime"


class SuspiciousImsisReport(BaseReport):
    name = "IMSIs/IMEIs Sospechosos"
    filename_prefix = "imsis_sospechosos"

    def __init__(self, db: Client) -> None:
        self.db = db

    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        cutoff = _cutoff_date()

        if date_from >= cutoff:
            rows = self._query(date_from, date_to, _HOT_TABLE, _HOT_TIME)
        elif date_to <= cutoff:
            rows = self._query(date_from, date_to, _COLD_TABLE, _COLD_TIME)
        else:
            hot = self._query(cutoff, date_to, _HOT_TABLE, _HOT_TIME)
            cold = self._query(date_from, cutoff, _COLD_TABLE, _COLD_TIME)
            rows = self._merge(hot, cold)

        return self._to_strings(rows)

    def _query(
        self,
        date_from: datetime,
        date_to: datetime,
        table: str,
        time_col: str,
    ) -> list[dict]:
        sql = f"""
            WITH user_numbers AS (
                SELECT
                    imsi,
                    CASE WHEN direction = 'S' THEN num_a ELSE num_b END AS msisdn
                FROM {table}
                WHERE {time_col} >= {{from_dt:DateTime}}
                  AND {time_col} < {{to_dt:DateTime}}
            )
            SELECT
                c.imsi,
                groupUniqArray(u.msisdn)   AS numeros_usuario,
                uniqExact(c.imei)          AS total_imeis,
                groupUniqArray(c.imei)     AS imeis_asociados,
                COUNT(*)                   AS total_eventos,
                MIN(c.{time_col})          AS primer_evento,
                MAX(c.{time_col})          AS ultimo_evento
            FROM {table} c
            JOIN user_numbers u ON u.imsi = c.imsi
            WHERE c.{time_col} >= {{from_dt:DateTime}}
              AND c.{time_col} < {{to_dt:DateTime}}
            GROUP BY c.imsi
            HAVING uniqExact(c.imei) > 1
            ORDER BY total_imeis DESC, total_eventos DESC
        """
        result = self.db.query(sql, parameters={"from_dt": date_from, "to_dt": date_to})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def _merge(self, hot: list[dict], cold: list[dict]) -> list[dict]:
        combined: dict[str, dict] = {}

        for row in hot + cold:
            imsi = row["imsi"]
            if imsi not in combined:
                combined[imsi] = {
                    "imsi": imsi,
                    "numeros_set": set(),
                    "imeis_set": set(),
                    "total_eventos": 0,
                    "primer_evento": row["primer_evento"],
                    "ultimo_evento": row["ultimo_evento"],
                }
            entry = combined[imsi]
            entry["numeros_set"].update(row["numeros_usuario"] if isinstance(row["numeros_usuario"], list) else [row["numeros_usuario"]])
            entry["imeis_set"].update(row["imeis_asociados"] if isinstance(row["imeis_asociados"], list) else [row["imeis_asociados"]])
            entry["total_eventos"] += row["total_eventos"]
            if row["primer_evento"] < entry["primer_evento"]:
                entry["primer_evento"] = row["primer_evento"]
            if row["ultimo_evento"] > entry["ultimo_evento"]:
                entry["ultimo_evento"] = row["ultimo_evento"]

        result = []
        for entry in combined.values():
            imeis = entry["imeis_set"]
            if len(imeis) > 1:
                result.append({
                    "imsi": entry["imsi"],
                    "numeros_usuario": sorted(entry["numeros_set"]),
                    "imeis_asociados": sorted(imeis),
                    "total_imeis": len(imeis),
                    "total_eventos": entry["total_eventos"],
                    "primer_evento": entry["primer_evento"],
                    "ultimo_evento": entry["ultimo_evento"],
                })

        return sorted(result, key=lambda r: (-r["total_imeis"], -r["total_eventos"]))

    def _to_strings(self, rows: list[dict]) -> list[dict]:
        for row in rows:
            if isinstance(row.get("numeros_usuario"), list):
                row["numeros_usuario"] = ", ".join(str(v) for v in row["numeros_usuario"])
            if isinstance(row.get("imeis_asociados"), list):
                row["imeis_asociados"] = ", ".join(str(v) for v in row["imeis_asociados"])
            if "imeis_set" not in row:
                row["total_imeis"] = row.get("total_imeis", 0)
        return rows

    def columns(self) -> list[tuple[str, str]]:
        return [
            ("IMSI", "imsi"),
            ("Números Usuario", "numeros_usuario"),
            ("Total IMEIs", "total_imeis"),
            ("IMEIs Asociados", "imeis_asociados"),
            ("Total Eventos", "total_eventos"),
            ("Primer Evento", "primer_evento"),
            ("Último Evento", "ultimo_evento"),
        ]

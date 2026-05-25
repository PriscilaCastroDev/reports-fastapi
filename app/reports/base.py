from abc import ABC, abstractmethod
from datetime import datetime
from io import BytesIO

from clickhouse_connect.driver.client import Client

from app.services.excel_builder import build_excel


class BaseReport(ABC):
    name: str
    filename_prefix: str

    @abstractmethod
    def query(self, date_from: datetime, date_to: datetime) -> list[dict]:
        ...

    @abstractmethod
    def columns(self) -> list[tuple[str, str]]:
        """Returns [(header_label, dict_key), ...]. Empty list = auto-detect from rows."""
        ...

    def generate_excel(self, date_from: datetime, date_to: datetime) -> BytesIO:
        rows = self.query(date_from, date_to)
        return build_excel(rows, self.columns())

    def build_filename(self, period_label: str) -> str:
        return f"{self.filename_prefix}_{period_label}.xlsx"

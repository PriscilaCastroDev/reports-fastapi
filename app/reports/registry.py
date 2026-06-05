"""Catálogo único de reportes disponibles, compartido por el router de
descargas manuales y el scheduler de envíos automáticos."""

from app.reports.base import BaseReport
from app.reports.cdr_errors import CdrErrorsReport
from app.reports.compression_ratio import CompressionRatioReport
from app.reports.dropped_calls import DroppedCallsReport
from app.reports.duplicate_cdrs import DuplicateCDRsReport
from app.reports.duplicate_files import DuplicateFilesReport
from app.reports.suspicious_imsis import SuspiciousImsisReport
from app.reports.volume_by_record_type import VolumeByRecordTypeReport

REGISTRY: dict[str, type[BaseReport]] = {
    "duplicate-cdrs": DuplicateCDRsReport,
    "volume-by-record-type": VolumeByRecordTypeReport,
    "dropped-calls": DroppedCallsReport,
    "suspicious-imsis": SuspiciousImsisReport,
    "cdr-errors": CdrErrorsReport,
    "duplicate-files": DuplicateFilesReport,
    "compression-ratio": CompressionRatioReport,
}

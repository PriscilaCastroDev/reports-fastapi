from pydantic import BaseModel, Field


class ReportMeta(BaseModel):
    id: str = Field(..., description="Slug del reporte, usado como path parameter", example="volume-by-record-type")
    name: str = Field(..., description="Nombre legible del reporte", example="Volumen por Tipo de Registro")
    description: str = Field(..., description="Descripción del contenido del reporte")
    filename_prefix: str = Field(..., description="Prefijo del archivo .xlsx generado", example="distribucion_trafico")


class ReportListResponse(BaseModel):
    reports: list[ReportMeta]


class ErrorDetail(BaseModel):
    detail: str = Field(..., description="Descripción del error", example="Reporte 'foo' no encontrado")

-- Índices para acelerar los reportes CDR
-- Ejecutar en ClickHouse con un usuario con permisos ALTER TABLE

-- ============================================================
-- Tabla HOT: xdr.cdrs
-- ============================================================

-- Reporte: Llamadas caídas (duration = 0)
ALTER TABLE xdr.cdrs ADD INDEX IF NOT EXISTS idx_duration duration TYPE minmax GRANULARITY 1;
ALTER TABLE xdr.cdrs MATERIALIZE INDEX idx_duration;

-- Reporte: Todos los reportes filtran por event_time
-- (si event_time no está en el ORDER BY de la tabla, agregar este índice)
ALTER TABLE xdr.cdrs ADD INDEX IF NOT EXISTS idx_event_time event_time TYPE minmax GRANULARITY 1;
ALTER TABLE xdr.cdrs MATERIALIZE INDEX idx_event_time;

-- ============================================================
-- Tabla COLD: xdr.cdr_cold
-- ============================================================

ALTER TABLE xdr.cdr_cold ADD INDEX IF NOT EXISTS idx_duration duration TYPE minmax GRANULARITY 1;
ALTER TABLE xdr.cdr_cold MATERIALIZE INDEX idx_duration;

ALTER TABLE xdr.cdr_cold ADD INDEX IF NOT EXISTS idx_event_time eventTime TYPE minmax GRANULARITY 1;
ALTER TABLE xdr.cdr_cold MATERIALIZE INDEX idx_event_time;

-- ============================================================
-- Tabla: xdr.cdrs_errors (Reporte 4 - CDRs duplicados)
-- ============================================================

ALTER TABLE xdr.cdrs_errors ADD INDEX IF NOT EXISTS idx_error_ts (error_description, ts) TYPE minmax GRANULARITY 1;
ALTER TABLE xdr.cdrs_errors MATERIALIZE INDEX idx_error_ts;

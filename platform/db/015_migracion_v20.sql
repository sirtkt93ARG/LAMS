-- Cancelación explícita de actividades abiertas, sin borrar entregas ni historial.
ALTER TABLE open_assignments ADD COLUMN IF NOT EXISTS cancelled_at timestamptz;
ALTER TABLE open_assignments ADD COLUMN IF NOT EXISTS cancellation_reason text;

-- La API actualiza únicamente los metadatos de cancelación; RLS limita el cambio al tenant activo.
GRANT UPDATE ON open_assignments TO matheval_app;

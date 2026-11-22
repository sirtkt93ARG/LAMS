-- Cancelación explícita de actividades abiertas, sin borrar entregas ni historial.
ALTER TABLE open_assignments ADD COLUMN IF NOT EXISTS cancelled_at timestamptz;
ALTER TABLE open_assignments ADD COLUMN IF NOT EXISTS cancellation_reason text;

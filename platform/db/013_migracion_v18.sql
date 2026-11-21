-- Biblioteca de rúbricas por competencia: cada actividad conserva el esquema usado al crearla.
ALTER TABLE open_assignments ADD COLUMN IF NOT EXISTS competency_id text;
ALTER TABLE open_assignments ADD COLUMN IF NOT EXISTS rubric_snapshot jsonb;

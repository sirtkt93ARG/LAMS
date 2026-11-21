-- Evita perder respuestas cuando dos solicitudes compiten por la misma sesión.
-- Las versiones se incrementan en cada escritura; las respuestas se guardan junto con el estado en una transacción.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 0;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM responses
    GROUP BY tenant_id, session_id, item_id
    HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION
      'Hay respuestas duplicadas por sesión/ítem. Conciliá los registros existentes antes de aplicar la migración 008.';
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_responses_session_item
  ON responses (tenant_id, session_id, item_id);

-- Migración para bases PostgreSQL creadas con la versión 0.3/0.4 (NO PROBADA). Ejecutar con el rol propietario.
ALTER TABLE sessions  ADD COLUMN IF NOT EXISTS course_id text;
ALTER TABLE sessions  ADD COLUMN IF NOT EXISTS course_label text;
ALTER TABLE responses ADD COLUMN IF NOT EXISTS hints integer NOT NULL DEFAULT 0;
ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_mode_check;
ALTER TABLE sessions ADD CONSTRAINT sessions_mode_check CHECK (mode IN ('practica', 'medicion', 'dirigida', 'piloto'));

CREATE TABLE IF NOT EXISTS tenant_settings (
  tenant_id text PRIMARY KEY, consent_attested_at timestamptz, consent_attested_by text, retention_days integer NOT NULL DEFAULT 365);
CREATE TABLE IF NOT EXISTS audit_log (
  id bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(), tenant_id text, actor text NOT NULL, action text NOT NULL, detail text);

DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['tenant_settings', 'audit_log'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($p$CREATE POLICY tenant_isolation ON %I
      USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))
      WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))$p$, t);
  END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON sessions, responses, tenant_settings TO matheval_app;
GRANT SELECT, INSERT ON item_reviews, audit_log TO matheval_app;
GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO matheval_app;

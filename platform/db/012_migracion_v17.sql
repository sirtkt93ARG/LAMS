-- Entregas de preguntas abiertas y corrección docente, aisladas por escuela.
CREATE TABLE IF NOT EXISTS open_assignments (
  id text PRIMARY KEY,
  tenant_id text NOT NULL,
  course_id text,
  item_id text NOT NULL,
  title text NOT NULL,
  instructions text NOT NULL DEFAULT '',
  assigned_by text NOT NULL,
  due_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_open_assignments_tenant_course ON open_assignments (tenant_id, course_id);

CREATE TABLE IF NOT EXISTS open_submissions (
  id text PRIMARY KEY,
  assignment_id text NOT NULL REFERENCES open_assignments(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  pid text NOT NULL,
  response text NOT NULL,
  status text NOT NULL DEFAULT 'pendiente' CHECK (status IN ('pendiente', 'corregida')),
  score double precision CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
  feedback text,
  rubric jsonb,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  reviewed_by text,
  reviewed_at timestamptz,
  UNIQUE (tenant_id, assignment_id, pid)
);
CREATE INDEX IF NOT EXISTS ix_open_submissions_tenant_status ON open_submissions (tenant_id, status);

DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['open_assignments', 'open_submissions'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($p$CREATE POLICY tenant_isolation ON %I
      USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))
      WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))$p$, t);
  END LOOP;
END $$;

GRANT SELECT, INSERT ON open_assignments TO matheval_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON open_submissions TO matheval_app;

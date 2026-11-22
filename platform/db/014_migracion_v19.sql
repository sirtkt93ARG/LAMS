-- Historial de intentos de respuestas abiertas y reentregas tras corrección.
-- La tabla anterior se conserva para compatibilidad y se copia como intento inicial.
CREATE TABLE IF NOT EXISTS open_submission_attempts (
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
  attempt_number integer NOT NULL CHECK (attempt_number > 0),
  UNIQUE (tenant_id, assignment_id, pid, attempt_number)
);
CREATE INDEX IF NOT EXISTS ix_open_attempts_tenant_assignment
  ON open_submission_attempts (tenant_id, assignment_id, pid, attempt_number);
CREATE INDEX IF NOT EXISTS ix_open_attempts_tenant_status
  ON open_submission_attempts (tenant_id, status);

INSERT INTO open_submission_attempts
  (id, assignment_id, tenant_id, pid, response, status, score, feedback, rubric,
   submitted_at, reviewed_by, reviewed_at, attempt_number)
SELECT id, assignment_id, tenant_id, pid, response, status, score, feedback, rubric,
       submitted_at, reviewed_by, reviewed_at, 1
FROM open_submissions
ON CONFLICT (id) DO NOTHING;

ALTER TABLE open_submission_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE open_submission_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON open_submission_attempts
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''));

GRANT SELECT, INSERT, UPDATE, DELETE ON open_submission_attempts TO matheval_app;

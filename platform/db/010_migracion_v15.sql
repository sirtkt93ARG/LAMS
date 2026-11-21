-- Bloquea exportaciones xAPI futuras tras una solicitud de supresión local.
-- La fila es un tombstone persistente, aislado por escuela y hash del seudónimo.
CREATE TABLE IF NOT EXISTS xapi_erasure_blocks (
  tenant_id text NOT NULL,
  pid_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, pid_hash)
);

ALTER TABLE xapi_erasure_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE xapi_erasure_blocks FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON xapi_erasure_blocks
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''));

GRANT SELECT, INSERT ON xapi_erasure_blocks TO matheval_app;

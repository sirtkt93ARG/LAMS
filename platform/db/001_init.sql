-- Esquema PostgreSQL equivalente al de api/app/store.py (SQLite). NO PROBADO en este entorno (sin PostgreSQL).
-- Aislamiento por escuela con seguridad a nivel de fila (RLS). La API opera con el rol `matheval_app`
-- (sin BYPASSRLS) y ejecuta, dentro de cada transacción: SELECT set_config('app.tenant_id', '<escuela>', true);
-- Solo se guarda el identificador seudónimo (pid): nunca el identificador real del usuario.

CREATE TABLE sessions (
  id          text PRIMARY KEY,
  tenant_id   text NOT NULL,
  pid         text NOT NULL,
  mode        text NOT NULL CHECK (mode IN ('practica', 'medicion', 'dirigida', 'piloto')),
  state       jsonb NOT NULL,
  result      jsonb,
  started_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  course_id   text,
  course_label text
);
CREATE INDEX ix_sessions_tenant ON sessions (tenant_id);

CREATE TABLE responses (
  id          bigserial PRIMARY KEY,
  tenant_id   text NOT NULL,
  session_id  text NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  item_id     text NOT NULL,
  response    text,
  score       real,
  error_tag   text,
  duration_s  real,
  answered_at timestamptz NOT NULL DEFAULT now(),
  hints       integer NOT NULL DEFAULT 0
);
CREATE INDEX ix_responses_session ON responses (tenant_id, session_id);

CREATE TABLE used_tokens (
  jti text PRIMARY KEY,
  used_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tenant_networks (
  network_id text NOT NULL,
  tenant_id text NOT NULL,
  accepted boolean NOT NULL DEFAULT false,
  PRIMARY KEY (network_id, tenant_id)
);

CREATE TABLE tenant_settings (
  tenant_id           text PRIMARY KEY,
  consent_attested_at timestamptz,
  consent_attested_by text,
  retention_days      integer NOT NULL DEFAULT 365
);

CREATE TABLE audit_log (
  id        bigserial PRIMARY KEY,
  at        timestamptz NOT NULL DEFAULT now(),
  tenant_id text,
  actor     text NOT NULL,
  action    text NOT NULL,
  detail    text
);

-- Revisiones docentes de plantillas: no pertenecen a una escuela (sin RLS).
CREATE TABLE item_reviews (
  id         bigserial PRIMARY KEY,
  scope      text NOT NULL,
  reviewer   text NOT NULL,
  decision   text NOT NULL CHECK (decision IN ('aprobar', 'rechazar')),
  comment    text,
  checklist  jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scope, reviewer)
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'matheval_app') THEN
    CREATE ROLE matheval_app LOGIN PASSWORD 'cambiar-en-produccion' NOBYPASSRLS;
  END IF;
END $$;

DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['sessions', 'responses', 'tenant_settings', 'audit_log'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($p$CREATE POLICY tenant_isolation ON %I
      USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))
      WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))$p$, t);
  END LOOP;
END $$;

-- Una escuela solo puede ver invitaciones dirigidas a ella; una red solo sus propias membresías.
ALTER TABLE tenant_networks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_networks FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_network_membership_select ON tenant_networks
  FOR SELECT USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  );
-- Only the network may create invitations. Schools may only accept/decline their own pending invitation.
CREATE POLICY tenant_network_invite_insert ON tenant_networks
  FOR INSERT WITH CHECK (network_id = NULLIF(current_setting('app.tenant_id', true), ''));
CREATE POLICY tenant_network_invite_update ON tenant_networks
  FOR UPDATE USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '') AND accepted = false
  ) WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''));
CREATE POLICY tenant_network_invite_delete ON tenant_networks
  FOR DELETE USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  );

GRANT SELECT, INSERT, DELETE ON sessions, responses, tenant_settings TO matheval_app;
GRANT UPDATE ON sessions, tenant_settings TO matheval_app;
GRANT SELECT, INSERT, DELETE ON tenant_networks TO matheval_app;
GRANT UPDATE (accepted) ON tenant_networks TO matheval_app;
GRANT SELECT, INSERT ON item_reviews, audit_log TO matheval_app;
GRANT SELECT, INSERT, DELETE ON used_tokens TO matheval_app;
GRANT USAGE, SELECT ON SEQUENCE responses_id_seq, item_reviews_id_seq, audit_log_id_seq TO matheval_app;

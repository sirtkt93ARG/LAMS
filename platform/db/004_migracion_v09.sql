-- Migración de gobierno de redes para instalaciones PostgreSQL existentes.
-- Las membresías nuevas quedan pendientes hasta que la escuela las acepte.
CREATE TABLE IF NOT EXISTS tenant_networks (
  network_id text NOT NULL,
  tenant_id text NOT NULL,
  accepted boolean NOT NULL DEFAULT false,
  PRIMARY KEY (network_id, tenant_id)
);
ALTER TABLE tenant_networks ADD COLUMN IF NOT EXISTS accepted boolean NOT NULL DEFAULT false;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_networks TO matheval_app;

-- Aislamiento por tenant: la red ve sus membresías y la escuela sus invitaciones.
ALTER TABLE tenant_networks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_networks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_network_membership_access ON tenant_networks;
CREATE POLICY tenant_network_membership_access ON tenant_networks
  USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  )
  WITH CHECK (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  );

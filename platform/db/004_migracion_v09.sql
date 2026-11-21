-- Migración de gobierno de redes para instalaciones PostgreSQL existentes.
-- Las membresías nuevas quedan pendientes hasta que la escuela las acepte.
CREATE TABLE IF NOT EXISTS tenant_networks (
  network_id text NOT NULL,
  tenant_id text NOT NULL,
  accepted boolean NOT NULL DEFAULT false,
  PRIMARY KEY (network_id, tenant_id)
);
ALTER TABLE tenant_networks ADD COLUMN IF NOT EXISTS accepted boolean NOT NULL DEFAULT false;
REVOKE UPDATE ON tenant_networks FROM matheval_app;
GRANT SELECT, INSERT, DELETE ON tenant_networks TO matheval_app;
GRANT UPDATE (accepted) ON tenant_networks TO matheval_app;

-- Aislamiento por tenant: la red crea invitaciones; la escuela solo ve y responde las propias.
ALTER TABLE tenant_networks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_networks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_network_membership_access ON tenant_networks;
DROP POLICY IF EXISTS tenant_network_membership_select ON tenant_networks;
DROP POLICY IF EXISTS tenant_network_invite_insert ON tenant_networks;
DROP POLICY IF EXISTS tenant_network_invite_update ON tenant_networks;
DROP POLICY IF EXISTS tenant_network_invite_delete ON tenant_networks;
CREATE POLICY tenant_network_membership_select ON tenant_networks
  FOR SELECT USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  );
CREATE POLICY tenant_network_invite_insert ON tenant_networks
  FOR INSERT WITH CHECK (network_id = NULLIF(current_setting('app.tenant_id', true), ''));
CREATE POLICY tenant_network_invite_update ON tenant_networks
  FOR UPDATE USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '') AND accepted = false
  ) WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''));
CREATE POLICY tenant_network_invite_delete ON tenant_networks
  FOR DELETE USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR (tenant_id = NULLIF(current_setting('app.tenant_id', true), '') AND accepted = false)
  );

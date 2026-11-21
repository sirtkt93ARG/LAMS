-- Migración v11: permitir que una escuela retire el consentimiento de compartir datos agregados.
-- La red también puede eliminar sus propios vínculos; una escuela solo puede eliminar vínculos donde es tenant_id.
DROP POLICY IF EXISTS tenant_network_invite_delete ON tenant_networks;
CREATE POLICY tenant_network_invite_delete ON tenant_networks
  FOR DELETE USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  );

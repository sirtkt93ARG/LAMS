-- Permite retirar el consentimiento después de haber aceptado una invitación.
-- La escuela solo puede eliminar la membresía cuyo tenant_id coincide con su contexto RLS.
DROP POLICY IF EXISTS tenant_network_invite_delete ON tenant_networks;
CREATE POLICY tenant_network_invite_delete ON tenant_networks
  FOR DELETE USING (
    network_id = NULLIF(current_setting('app.tenant_id', true), '')
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')
  );

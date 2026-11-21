-- Migración de seguridad para instalaciones PostgreSQL existentes.
-- Ejecutar como propietario de la base antes de desplegar la versión que consume handoffs LTI.
CREATE TABLE IF NOT EXISTS used_tokens (
  jti text PRIMARY KEY,
  used_at timestamptz NOT NULL DEFAULT now()
);
GRANT INSERT, DELETE ON used_tokens TO matheval_app;

-- Invitaciones entre redes y escuelas: las relaciones nuevas empiezan pendientes.
CREATE TABLE IF NOT EXISTS tenant_networks (
  network_id text NOT NULL,
  tenant_id text NOT NULL,
  accepted boolean NOT NULL DEFAULT false,
  PRIMARY KEY (network_id, tenant_id)
);
ALTER TABLE tenant_networks ADD COLUMN IF NOT EXISTS accepted boolean NOT NULL DEFAULT false;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_networks TO matheval_app;

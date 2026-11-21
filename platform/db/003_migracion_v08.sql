-- Migración de seguridad para instalaciones PostgreSQL existentes.
-- Ejecutar como propietario de la base antes de desplegar la versión que consume handoffs LTI.
CREATE TABLE IF NOT EXISTS used_tokens (
  jti text PRIMARY KEY,
  used_at timestamptz NOT NULL DEFAULT now()
);
GRANT INSERT, DELETE ON used_tokens TO matheval_app;

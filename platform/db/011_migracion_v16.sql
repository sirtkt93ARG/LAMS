-- Contadores globales de rate limiting compartidos entre todos los workers.
-- La clave se almacena como SHA-256; no se guardan identificadores de usuario ni IPs.
CREATE TABLE IF NOT EXISTS rate_limit_windows (
  key_hash text PRIMARY KEY,
  window_start bigint NOT NULL,
  hits integer NOT NULL CHECK (hits > 0)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON rate_limit_windows TO matheval_app;

-- Permite que el almacén limpie JTIs vencidos y consuma cada handoff una sola vez.
-- El DELETE filtra por used_at, por lo que PostgreSQL también requiere SELECT.
GRANT SELECT, INSERT, DELETE ON used_tokens TO matheval_app;

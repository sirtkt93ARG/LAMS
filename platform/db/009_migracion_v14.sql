-- Permite anonimizar el actor y el detalle de eventos del usuario que solicita supresión local.
-- La política RLS tenant_isolation de audit_log sigue limitando la operación a su escuela.
GRANT UPDATE (actor, detail) ON audit_log TO matheval_app;

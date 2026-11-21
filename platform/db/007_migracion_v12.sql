-- La API actualiza el estado/resultado de sesiones y hace upsert del consentimiento escolar.
-- Sin estos permisos, el primer envío de respuesta o una segunda confirmación de consentimiento falla.
GRANT UPDATE ON sessions, tenant_settings TO matheval_app;

# LTI Names and Role Provisioning Services (NRPS)

Matheval puede consultar el roster del contexto LTI 1.3 para mostrar al docente el nombre de un estudiante en lugar de su etiqueta seudónima. La consulta es de solo lectura y no crea una tabla local de usuarios ni almacena nombres o correos.

## Requisitos del LMS

- El lanzamiento debe incluir el claim `https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice`, con `context_memberships_url` y `service_versions: ["2.0"]`.
- El registro de la herramienta debe tener habilitado el scope OAuth `https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly`.
- La URL del servicio debe usar HTTPS fuera de desarrollo.
- El registro LTI de Matheval debe declarar `nrps_allowed_hosts` con los nombres de host exactos que el LMS usa para el endpoint NRPS. Si el host coincide con el issuer, el generador de claves lo propone por defecto; si el LMS separa issuer y API, agregá el host de API explícitamente.

Ejemplo ilustrativo de un registro LTI (no reemplaza las URLs ni claves reales):

```json
{
  "client_id": "identificador-del-cliente",
  "auth_token_url": "https://lms.example/oauth/token",
  "nrps_allowed_hosts": ["lms.example", "api.lms.example"]
}
```

## Flujo y privacidad

1. PyLTI1p3 valida el lanzamiento y Matheval conserva en el token firmado únicamente issuer, client ID y URL del contexto NRPS.
2. Cuando un docente abre las entregas de una actividad, la API pide el roster al servicio LTI interno.
3. El servicio obtiene un token OAuth con el scope NRPS, consulta el endpoint y devuelve solo `user_id` y nombre visible de miembros con rol Learner y estado activo.
4. La API calcula el seudónimo del `user_id` recibido y asocia el nombre en memoria para esa respuesta HTTP. No escribe el nombre en SQLite, PostgreSQL, auditoría ni logs.
5. Si el claim, el scope, la conexión o la allowlist no están disponibles, la pantalla conserva la etiqueta seudónima.

El cliente no sigue redirecciones HTTP, valida el host en cada página de paginación, limita el roster a 10 páginas y 5000 miembros, y no solicita ni devuelve emails. El endpoint proxy interno requiere el secreto compartido entre API y servicio LTI.

## Validación y límites

CI prueba el flujo contra el LMS simulado: emisión del claim, OAuth NRPS, lectura de miembros, filtrado de docentes/cuentas inactivas, allowlist y sesión docente. Esto no demuestra compatibilidad con una instancia Moodle u otro LMS institucional. Antes de habilitarlo en una institución, verificá el claim, los scopes concedidos, el host real y la respuesta NRPS con una cuenta docente de prueba.

La vista de nombres depende del roster actual del LMS. No es una fuente de identidad histórica ni reemplaza la gestión de matrícula del LMS. Si un alumno deja de aparecer en el roster, Matheval no conserva una copia local de su nombre.

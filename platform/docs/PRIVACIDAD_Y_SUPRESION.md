# Privacidad y supresión de datos

## Qué elimina la plataforma

`DELETE /v1/me/data` elimina de la base local las sesiones y respuestas asociadas al seudónimo del usuario dentro de su escuela. En la misma operación anonimiza los eventos de auditoría cuyo actor coincide con el usuario, conservando el evento sin el identificador ni el detalle que pudiera volver a vincularlo.

La respuesta incluye los conteos de sesiones, respuestas y eventos de auditoría anonimizados. La auditoría conserva un evento mínimo de tipo `supresion_local_de_datos`, registrado por `system`, sin guardar el seudónimo del estudiante.

## Si no hay un LRS externo

Cuando `LRS_URL` no está configurado, la respuesta indica `external_lrs.status = not_configured` y `erasure_complete = true` para los datos gestionados por esta plataforma.

## Si hay un LRS externo

Cuando `LRS_URL` está configurado, la plataforma elimina los datos locales, pero devuelve HTTP **202 Accepted**, `erasure_complete = false` y `external_lrs.status = manual_action_required`. También devuelve el objeto Agent exacto usado en las sentencias xAPI para que el responsable institucional pueda localizar los registros.

Esto no es un detalle de implementación que podamos resolver con un `DELETE` genérico. La especificación xAPI 1.0.3 establece que los Statements son inmutables y permanentes; la operación estándar para invalidarlos es *voiding*, que no los destruye. Por tanto, voiding no equivale a borrado definitivo ni demuestra por sí solo el cumplimiento de un derecho de supresión.

- Especificación oficial: [xAPI — Statement Lifecycle, Immutability y Voiding](https://github.com/adlnet/xAPI-Spec/blob/master/xAPI-Data.md#232-voiding).
- El LRS concreto debe proporcionar un procedimiento administrativo de supresión o una política de retención compatible con las obligaciones de la institución.
- La plataforma no afirma haber borrado Statements externos. Hasta integrar y probar el mecanismo administrativo del LRS elegido, la respuesta 202 deja la acción externa explícitamente pendiente.

## Antes de habilitar xAPI en producción

1. Identificar el proveedor y versión exacta del LRS.
2. Acordar con la institución el procedimiento de acceso, supresión, retención, backups y evidencias.
3. Implementar un adaptador específico con autenticación, paginación, control de errores y confirmación de borrado.
4. Probarlo con datos sintéticos y verificar también réplicas, índices, exportaciones y backups del proveedor.
5. Solo entonces cambiar el estado de la solicitud a completado.

La escuela o institución es responsable de definir la base legal, los plazos y las instrucciones aplicables. Esta guía describe el comportamiento técnico actual; no sustituye una revisión jurídica.

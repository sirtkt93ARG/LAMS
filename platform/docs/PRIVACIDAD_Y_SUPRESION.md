# Privacidad y supresión de datos

## Qué elimina la plataforma

`DELETE /v1/me/data` elimina de la base local las sesiones, respuestas de práctica y todos los intentos de actividades abiertas asociados al seudónimo del usuario dentro de su escuela. El historial de entregas no sobrevive a una solicitud de supresión del estudiante. En la misma operación anonimiza los eventos de auditoría cuyo actor coincide con el usuario, conservando el evento sin el identificador ni el detalle que pudiera volver a vincularlo.

La respuesta incluye los conteos de sesiones, respuestas y eventos de auditoría anonimizados, además de `future_xapi_exports_blocked = true` y `suppression_marker_retained = true`. Para impedir que un trabajo pendiente vuelva a exportar datos, se conserva un marcador técnico mínimo por escuela: un SHA-256 del seudónimo, no el seudónimo original. Este marcador sigue siendo un dato seudónimo vinculable por el sistema y debe tratarse como tal; no se presenta como borrado absoluto de todo dato relacionado. La auditoría conserva un evento mínimo de tipo `supresion_local_de_datos`, registrado por `system`, sin guardar el seudónimo del estudiante.

## Si no hay un LRS externo

Cuando `LRS_URL` no está configurado, la respuesta indica `external_lrs.status = not_configured_currently`. `erasure_complete` queda en `null`: la configuración actual no demuestra que nunca se hayan enviado Statements a un LRS en el pasado.

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

## Coordinación con exportaciones xAPI pendientes

Cada envío xAPI en segundo plano se ejecuta bajo un bloqueo transaccional compartido con la supresión local. Si el envío obtiene primero el bloqueo, la supresión espera a que termine; si la supresión obtiene primero el bloqueo, el envío pendiente se descarta. La supresión crea además una marca persistente por escuela y hash SHA-256 del seudónimo (tabla xapi_erasure_blocks), que impide exportaciones posteriores de ese mismo seudónimo, incluso si se inicia otra sesión. No se almacena el seudónimo xAPI directamente en esa tabla.

En PostgreSQL, el bloqueo usa un advisory lock transaccional y la marca está protegida por RLS. En SQLite, se usa una transacción de escritura BEGIN IMMEDIATE. El envío externo ocurre mientras se mantiene el bloqueo; por eso el timeout HTTP está acotado y la supresión puede tener que esperar a un envío en curso.

Esta coordinación requiere que todas las instancias de la API ejecuten esta versión antes de considerar cubierta la carrera. Durante un despliegue gradual, hay que detener o drenar las instancias antiguas que todavía puedan enviar Statements sin tomar el bloqueo. La marca no elimina Statements ya aceptados por el LRS: sigue siendo necesaria la acción administrativa externa descrita arriba.

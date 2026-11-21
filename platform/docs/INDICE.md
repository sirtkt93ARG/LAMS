# Índice de la documentación

Empezá por `README.md` (qué es, cómo montarlo y estado real de cada pieza). Después, según lo que necesites:

| Querés… | Leé |
|---|---|
| Montar y probar la plataforma | `README.md` (sección «Cómo montarlo») |
| Saber qué funcionalidades hay y cuáles se evaluaron o descartaron | `docs/FUNCIONALIDADES.md` |
| Ver los riesgos, hallazgos de la auditoría, simulaciones e ideas para ampliar | `docs/AUDITORIA.md` |
| Aplicar los arreglos de la auditoría (propuestas) | `docs/arreglos_auditoria/LEEME.md` |
| Entender la arquitectura, el análisis legal, el marco de matemática y el plan | `docs/DOCUMENTO_DE_ARQUITECTURA.md` (enlace al documento completo de 25 secciones) |
| Cargar microdatos de PISA y obtener errores estándar y brechas | `docs/MICRODATOS_PISA.md` |
| Conocer las fuentes y los límites de los datos del observatorio | `data/observatory/FUENTES.md` |
| Revisar el esquema de base de datos | `db/001_init.sql`, `db/002_migracion_v05.sql` |
| Ver el despliegue y la configuración de Keycloak | `deploy/` |

## Mapa del código

| Carpeta | Contenido |
|---|---|
| `src/matheval` | Núcleo: plantillas de ejercicios, corrección segura, QTI 3, motor adaptativo (multietapa y CAT), calibración, habilidades y dominio, práctica dirigida, explicaciones, xAPI, observatorio de resultados históricos y estadística de microdatos de PISA |
| `api/` | API (FastAPI): sesiones, práctica por tema, panel docente, tendencias, red de escuelas, observatorio, consentimiento, borrado de datos, auditoría |
| `lti_service/`, `tools/mock_lms/` | Ingreso por LTI 1.3 y devolución de notas; aula virtual simulada para probarlo sin Moodle |
| `web/` | Interfaz (Next.js): práctica, resultados, progreso, panel docente, revisión, análisis, observatorio, red e informe imprimible |
| `db/`, `deploy/` | Esquema PostgreSQL con aislamiento por escuela, Docker, Keycloak |
| `scripts/` | Arranque en un comando, banco de demostración, calibración, simulación, ingreso de microdatos, pruebas de humo, verificación de PostgreSQL |
| `tests/` | 91 pruebas automáticas |
| `data/` | Banco de demostración, QTI de muestra y datos del observatorio |

## Historial de versiones

| Versión | Qué sumó |
|---|---|
| 0.1 | Núcleo: plantillas, corrección, QTI 3, IRT, multietapa y CAT, calibración, xAPI, banco con estados |
| 0.2 | Interfaz web y API para el recorrido del estudiante y del docente |
| 0.3 | Persistencia de sesiones y revisión docente por plantilla; plantillas hasta N8 |
| 0.4 | Aula virtual simulada, servicio LTI, pruebas de humo y verificación de PostgreSQL |
| 0.5 | Habilidades, dominio, práctica por tema con pistas y ejercicios espejo, 24 plantillas, notas al LMS, consentimiento, accesibilidad |
| 0.6 | Observatorio de PISA 2000-2025, tendencias, vista de red e informe imprimible |
| 0.7 | Microdatos de PISA: errores estándar, brechas por nivel socioeconómico y género, pruebas de cambio entre ciclos |
| (auditoría) | Informe con hallazgos y arreglos propuestos: `docs/AUDITORIA.md` y `docs/arreglos_auditoria/` (no aplicados en este paquete) |

## Estado real de este paquete

- **Probado con pruebas automáticas:** núcleo, lógica de la API, almacén, servicio LTI con sustitutos, devolución de notas por HTTP contra el aula simulada, estadística de PISA con simulaciones.
- **Verificado por quien montó la v0.2:** recorrido del estudiante y del docente con FastAPI y Next.js reales.
- **Sin ejecutar:** PyLTI1p3 real, PostgreSQL, Docker, Keycloak, almacén de xAPI y todo lo de la web posterior a la v0.2.
- **Sin datos reales:** calibración con piloto y microdatos de PISA.

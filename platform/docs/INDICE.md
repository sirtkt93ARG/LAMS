# Índice de la documentación

Empezá por `README.md` (qué es, cómo montarlo y estado real de cada pieza). Después, según lo que necesites:

| Querés… | Leé |
|---|---|
| Montar y probar la plataforma | `README.md` (sección «Cómo montarlo») |
| Saber qué funcionalidades hay y cuáles se evaluaron o descartaron | `docs/FUNCIONALIDADES.md` |
| Ver los riesgos, hallazgos de la auditoría, simulaciones e ideas para ampliar | `docs/AUDITORIA.md` |
| Consultar el registro histórico de parches y decisiones de auditoría | `docs/arreglos_auditoria/LEEME.md` (no todos los elementos de esa carpeta representan tareas pendientes) |
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
| `tests/` | Suite Python/API/HTTP, integración PostgreSQL 16 y recorridos Playwright/axe en Chromium ejecutados en CI |
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

- **CI automatizado:** pruebas del núcleo, API y HTTP; integración PostgreSQL 16/RLS; PyLTI1p3 real con LMS simulado y devolución AGS; TypeScript, pruebas de librería, build Next.js y seis recorridos Playwright/axe en Chromium.
- **Stack local:** Docker Compose levanta PostgreSQL, Keycloak en modo desarrollo, API, LTI, LMS simulado y web. El smoke test completa una práctica de 24 respuestas y verifica la nota en el libro del LMS simulado.
- **Frontend:** Modern Web Guidance `legacy-scan` sin patrones heredados en los archivos revisados (38 guías y 52 reglas; alcance parcial, no auditoría integral).
- **Pendiente fuera de CI:** Moodle y Keycloak institucionales, LRS xAPI real, despliegue productivo, backups/restauración, monitorización y pruebas manuales con lectores de pantalla y dispositivos reales.
- **Validación educativa pendiente:** piloto con estudiantes, calibración con respuestas reales, puntos de corte N1–N8 y ejecución con microdatos oficiales de PISA.

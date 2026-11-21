# matheval: plataforma de evaluación adaptativa de matemática (v0.7)

Núcleo funcional del proyecto: ítems por plantillas verificados con SymPy, exportación QTI 3.0, motor adaptativo
(multietapa y CAT), calibración IRT, xAPI con identificadores seudónimos, y un banco con control de estados.
Alrededor: API (FastAPI), interfaz web (Next.js), servicio LTI 1.3, Keycloak, esquema PostgreSQL con RLS y Docker.

> **Documentación completa:** `docs/INDICE.md`. Incluye el informe de auditoría (`docs/AUDITORIA.md`) con hallazgos, simulaciones e ideas para ampliar la plataforma. Para copias y recuperación de PostgreSQL, consultá `docs/OPERACION_BACKUPS.md`.

## Estado real de cada pieza

| Pieza | Estado verificado |
|---|---|
| `src/matheval` (núcleo) | Implementado y cubierto por pruebas: 24 plantillas, habilidades, dominio, práctica dirigida, calibración y análisis. La calibración con respuestas de estudiantes reales y los puntos de corte siguen pendientes del piloto. |
| `api/` (FastAPI) | La suite Python y las pruebas HTTP pasan en CI. Hay 118 funciones de prueba distribuidas en `platform/tests/`; las cinco pruebas específicas de PostgreSQL se ejecutan en un job separado. |
| `lti_service/` y `tools/mock_lms/` | El flujo LTI 1.3 real con PyLTI1p3 —inicio de sesión, lanzamiento y devolución de nota— pasa por HTTP contra el LMS simulado en CI. **La integración con una instalación real de Moodle u otro LMS sigue pendiente.** |
| `web/` (Next.js 14) | TypeScript, pruebas de librería y build de producción pasan en CI. Ocho pruebas Playwright recorren login, práctica, panel docente, curaduría, red, navegación móvil, autorización de rutas y validación del formulario de invitación; axe-core comprueba reglas WCAG 2.1/2.2 AA y buenas prácticas. Falta la validación manual con lectores de pantalla y dispositivos/navegadores reales. |
| PostgreSQL | CI ejecuta migraciones, RLS y operaciones del almacén contra PostgreSQL 16. Hay una herramienta inicial para backup lógico verificado y restauración conservadora; falta ejecutar y documentar un ensayo end-to-end en PostgreSQL de staging. |
| Docker y Keycloak | El stack local de Docker Compose se construye y completa en CI el recorrido HTTP/LTI y la devolución AGS. Es una configuración de desarrollo, no un despliegue productivo; Moodle y Keycloak institucionales siguen pendientes. |

### Novedades de la v0.7: microdatos de PISA

- **Errores estándar y brechas:** `scripts/pisa_ingest.py` calcula, con los microdatos oficiales de la OCDE, medias con error estándar (replicación BRR y valores plausibles), porcentaje bajo el nivel 2 y brechas por nivel socioeconómico y género. El observatorio muestra bandas de confianza, pruebas de cambio entre ciclos y un panel de brechas. Guía paso a paso: `docs/MICRODATOS_PISA.md`.
- Hoy el panel de brechas está vacío: falta correr la carga con un archivo real (no pude descargarlos desde este entorno). El motor se validó con simulaciones.

### Novedades de la v0.6: más que ejercicios

- **Observatorio** (`/observatory`): resultados de PISA 2000-2025 en matemática, lectura y ciencias para Argentina, la región y países de referencia, con evolución, comparación por ciclo, brecha con la OCDE y fuente de cada dato. Los datos están en `data/observatory/pisa_agregados.csv` (cada fila con su fuente y su calidad: oficial o secundaria). Para ampliarlos, agregá filas y ejecutá `python scripts/validate_observatory.py`. Ver `data/observatory/FUENTES.md`.
- **Tendencias:** evolución mensual de los niveles del curso o la escuela y «Mi evolución» para cada estudiante.
- **Red o jurisdicción** (`/network`): resumen por escuela con supresión de grupos de menos de 10 estudiantes.
- **Informe imprimible** (`/teacher/report`).

### Novedades de la v0.5 (detalle y análisis en `docs/FUNCIONALIDADES.md`)

- **Aprendizaje:** 15 habilidades, dominio por habilidad, práctica por tema con ejercicios espejo, pistas, resolución paso a paso, repaso espaciado y recomendaciones, pantalla de progreso.
- **Contenido:** 12 plantillas nuevas (24 en total) con gráficos de barras y líneas, figuras, promedio, mediana, sistemas, Pitágoras e interés.
- **Calidad:** modo piloto, calibración por familia de ítems (`scripts/calibrate_from_db.py`) y análisis por plantilla.
- **Docentes:** cursos, errores frecuentes, dominio por tema, exportación CSV, análisis de ejercicios y confirmación de consentimiento.
- **LMS:** la nota (nivel de 1 a 8) vuelve al libro de calificaciones por LTI Advantage; el aula simulada tiene su libro en `http://localhost:8300/gradebook`.
- **Cumplimiento:** consentimiento institucional, retención y auditoría. `DELETE /v1/me/data` elimina datos locales; si hay un LRS externo devuelve 202 y exige la supresión administrativa del proveedor; si hoy no hay LRS configurado, no certifica que nunca se hayan enviado datos históricamente. Ver `docs/PRIVACIDAD_Y_SUPRESION.md`.
- **Robustez y accesibilidad:** respuestas idempotentes con reintentos, límites de frecuencia, métricas, tamaño de texto, alto contraste y lectura en voz alta.

## Cómo probar el núcleo

```bash
pip install sympy numpy scipy lxml
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/generate_bank.py      # banco de demostración + XML QTI 3
python scripts/simulate.py           # comparación de diseños con datos simulados
```

## Qué contiene el núcleo

- `templates.py`: 24 plantillas (T1 a T24, niveles objetivo N1 a N8). Cada ítem se recalcula de forma independiente
  y falla si la clave no coincide. Los distractores modelan errores típicos y llevan una etiqueta diagnóstica.
- `safe_expr.py`: lectura segura de expresiones del estudiante (sin `eval`; lista blanca y AST con límites).
- `qti3.py`: XML QTI 3.0. Sin red no se pudo validar contra el XSD oficial: validar con 1EdTech antes de importar.
- `adaptive.py`: diseño multietapa de 3 etapas con balance de contenido y CAT con control de exposición.
- `calibration.py`: calibración 2PL (EM) con datos faltantes, para el piloto. Recupera parámetros en simulación.
- `bank.py`: estados borrador a operativo; solo los calibrados miden; los ítems con IA exigen revisor; excluye
  licencias no comerciales.
- `xapi.py`, `ai_gateway.py`: sentencias xAPI con seudónimo (HMAC por inquilino) y pasarela de IA sin datos
  personales y sin chat libre.

## Resultado de la simulación (datos simulados, 3.000 estudiantes, 24 ítems)

Cohorte con ~73% por debajo de la hipótesis de nivel mínimo.

| Diseño | RMSE | RMSE en θ < -0,7 | Nivel exacto |
|---|---|---|---|
| Forma fija centrada en 0 | 0,492 | 0,530 | 56,6% |
| Forma fija centrada en la cohorte | 0,433 | 0,395 | 60,7% |
| Multietapa 8+8+8 | 0,366 | 0,369 | 65,6% |
| CAT con balance de contenido | 0,302 | 0,309 | 72,0% |

Es evidencia sobre el diseño del motor, no sobre estudiantes reales.

## Diseño de la interfaz

Hoja de cuaderno cuadriculado: cuadrícula celeste de fondo, hoja blanca con margen rojo y respuestas marcadas con
resaltador. Tipografía Atkinson Hyperlegible, sin tiempo límite, foco visible, contraste alto y teclado completo.
La interfaz y los metadatos ya usan el nombre Matheval. Antes del lanzamiento comercial todavía debe verificarse su disponibilidad registral mediante una búsqueda de marca.

## Límites que hay que tener presentes

1. Los puntos de corte de N1 a N8 y la correspondencia con categorías locales son **marcadores** (`levels.py`).
2. Las dificultades de los ítems son a priori. Para medir hace falta un piloto y `calibration.py`.
3. Hay una sola plantilla en varios niveles (N1, N2, N8): el banco necesita más plantillas y variedad de contextos antes del piloto.
4. Revisión legal pendiente: AGPL de TAO (no se usa aquí), licencias de dependencias, consentimiento y contrato de encargo.
5. `MATHEVAL_DEV=1` solo es para desarrollo: habilita usuarios por cabecera e ítems sin revisar.

## Cómo montarlo (en un equipo con red)

### Windows (PowerShell, desde la carpeta `platform`)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
.\scripts\dev.ps1            # instala lo que falta y abre 4 ventanas: API, servicio LTI, aula simulada y web
```

Cuando la web diga `Ready`, en otra terminal con el entorno activado:

```powershell
python scripts\smoke_http.py  # prueba por HTTP, incluido el ingreso completo por LTI
```

- Web: http://localhost:3000 (ingreso de desarrollo).
- Aula simulada: http://localhost:8300. Reemplaza a Moodle: «Entrar como estudiante» recorre el ingreso LTI 1.3 real
  hasta la práctica; «Entrar como docente» hasta el panel docente.
- `.\scripts\dev.ps1 -Prod` arranca sin atajos de desarrollo: solo se entra por el aula simulada, las plantillas
  quedan aprobadas con una revisión de demostración (`scripts/seed_reviews.py`, no es una revisión real) y hay que
  entrar primero como docente y confirmar el consentimiento para que los estudiantes puedan practicar.
- Para ver la devolución de notas: terminá una práctica como estudiante y abrí http://localhost:8300/gradebook.

### Mac / Linux

```bash
python -m venv .venv && ./scripts/dev.sh        # o ./scripts/dev.sh prod
```

### Pruebas automáticas

```bash
pip install -e ".[api,lti,dev,microdata]"
python -m pytest -q
```

CI ejecuta además la integración PostgreSQL contra PostgreSQL 16, el smoke test LTI con PyLTI1p3 real y el stack local de Docker Compose, incluida una práctica de 24 respuestas y la devolución de nota AGS. La API separa liveness (`/healthz`) de readiness (`/readyz`); el segundo comprueba la conexión a la base y es el healthcheck usado por Compose. El escaneo Modern Web Guidance no detectó patrones heredados en los archivos frontend revisados (38 guías y 52 reglas; es una revisión parcial, no una auditoría completa). Para el frontend, desde `web/`:

```bash
npm run typecheck
npm run test:lib
npm run build
npm run test:e2e
```

Las pruebas Playwright requieren que estén levantados API, LTI, LMS simulado y servidor web; el workflow de CI prepara esos servicios automáticamente.



### Stack local completo con Docker Compose

Desde la carpeta `platform`, ejecutá:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Incluye PostgreSQL, Keycloak en modo desarrollo, API, servicio LTI, LMS simulado y web. El smoke test de este stack pasa en CI, incluido el lanzamiento LTI, las 24 respuestas de práctica y la devolución de la calificación al libro del LMS simulado.

**Importante:** este Compose es exclusivamente para desarrollo local. Usa credenciales de demostración y Keycloak `start-dev`; no debe exponerse a Internet ni tratarse como configuración de producción. Para detenerlo sin borrar los datos locales, usá `docker compose -f deploy/docker-compose.yml down`. Agregá `-v` solo si querés eliminar también los volúmenes de la base y las claves efímeras.

### PostgreSQL con aislamiento por escuela (opcional, requiere Docker Desktop)

```bash
docker compose -f deploy/docker-compose.db.yml up -d
python scripts/check_postgres.py --admin-url postgresql://postgres:cambiar@localhost:5432/matheval --app-url postgresql://matheval_app:cambiar-en-produccion@localhost:5432/matheval
```

Si venís de una versión anterior, SQLite aplica sus migraciones compatibles al arrancar. En PostgreSQL existente, ejecutá con el propietario de la base las migraciones pendientes en orden, desde `db/002_migracion_v05.sql` hasta `db/011_migracion_v16.sql` (sin repetir las que ya aplicaste). La migración `004` deja las membresías de red existentes como pendientes: cada escuela debe aceptar de nuevo antes de compartir agregados. La migración `006` habilita retirar el consentimiento y salir de una red después de haber aceptado. La migración `008` incorpora control de versión y escritura atómica de respuestas; si detecta respuestas duplicadas históricas para la misma sesión e ítem, se detiene sin borrar datos y requiere conciliarlas antes de continuar. La migración `009` habilita la anonimización acotada de eventos de auditoría durante la supresión local. La `010` crea la marca persistente que bloquea exportaciones xAPI posteriores al borrado. La `011` crea los contadores compartidos de rate limiting (`rate_limit_windows`). **Antes de desplegar una versión que incluya la migración 011, aplicala en cada PostgreSQL existente con el propietario de la base**; los scripts de `/docker-entrypoint-initdb.d` solo se ejecutan al inicializar un volumen nuevo y no actualizan volúmenes ya creados.

Cuando algo falle, anotá el comando, el mensaje de error completo y las versiones de Node y Python. Los puntos que todavía requieren validación fuera de CI son la integración con Moodle/Keycloak reales, el despliegue productivo y las pruebas manuales de accesibilidad.

## Próximos pasos

1. **Integración institucional real:** probar el lanzamiento LTI y la devolución de calificaciones con una instalación de Moodle; completar la configuración de Keycloak con el proveedor de identidad que corresponda.
2. **Operación productiva:** definir HTTPS, gestión y rotación de secretos, backups y restauración de PostgreSQL, monitoreo, alertas, retención y respuesta ante incidentes.
3. **Accesibilidad y experiencia:** realizar pruebas manuales con teclado, lectores de pantalla, zoom/reflow y móviles reales; automatizar regresiones visuales cuando exista una línea base aprobada.
4. **Calidad psicométrica:** ampliar el banco (especialmente N2, N7 y N8), ejecutar un piloto con estudiantes, calibrar parámetros con respuestas reales y estudiar los puntos de corte antes de interpretar los niveles como mediciones validadas.
5. **Interoperabilidad de contenidos:** validar los XML QTI contra el XSD oficial de 1EdTech y probar importación/reproducción en herramientas externas; el flujo de importación todavía no está implementado.
6. **Gobernanza y privacidad:** revisar con especialistas el consentimiento, contratos, licencias, plazos de conservación y los procedimientos de acceso/supresión antes de un despliegue institucional.

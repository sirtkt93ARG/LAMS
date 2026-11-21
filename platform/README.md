# matheval: plataforma de evaluación adaptativa de matemática (v0.7)

Núcleo funcional del proyecto: ítems por plantillas verificados con SymPy, exportación QTI 3.0, motor adaptativo
(multietapa y CAT), calibración IRT, xAPI con identificadores seudónimos, y un banco con control de estados.
Alrededor: API (FastAPI), interfaz web (Next.js), servicio LTI 1.3, Keycloak, esquema PostgreSQL con RLS y Docker.

> **Documentación completa:** `docs/INDICE.md`. Incluye el informe de auditoría (`docs/AUDITORIA.md`) con hallazgos, simulaciones e ideas para ampliar la plataforma.

## Estado real de cada pieza

| Pieza | Estado |
|---|---|
| `src/matheval` (núcleo) | Implementado y probado: 24 plantillas (N1 a N8), habilidades, dominio, práctica dirigida, calibración, análisis |
| `api/` (FastAPI) | Lógica probada con 108 pruebas automáticas (más integración PostgreSQL en CI). Las pruebas por HTTP (`tests/test_http.py`) corren solo con FastAPI y httpx reales: **ejecutalas en tu equipo** |
| `lti_service/` y `tools/mock_lms/` | Ingreso LTI 1.3 y devolución de notas probados con sustitutos y por HTTP contra el LMS simulado. **Con PyLTI1p3 real, pendiente: `scripts/smoke_http.py`** |
| `web/` (Next.js 14) | Recorrido de estudiante y docente verificado por vos en la v0.2. **Todo lo nuevo (gráficos, práctica por tema, progreso, panel ampliado, accesibilidad) está sin ver en navegador** |
| PostgreSQL, Docker, Keycloak, Ralph | Escritos, **no ejecutados**. `scripts/check_postgres.py` verifica esquema y aislamiento por escuela |

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
- **Cumplimiento:** la escuela confirma el consentimiento antes de que se practique; derecho de supresión (`DELETE /v1/me/data`); retención (`scripts/purge_old.py`); auditoría.
- **Robustez y accesibilidad:** respuestas idempotentes con reintentos, límites de frecuencia, métricas, tamaño de texto, alto contraste y lectura en voz alta.

## Cómo probar el núcleo

```bash
pip install sympy numpy scipy lxml
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/generate_bank.py      # banco de demostración + XML QTI 3
python scripts/simulate.py           # comparación de diseños con datos simulados
```

## Qué contiene el núcleo

- `templates.py`: doce plantillas (T1 a T12, niveles objetivo N1 a N8). Cada ítem se recalcula de forma independiente
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
El nombre del producto es un marcador (`[Nombre del producto]`) hasta resolver la búsqueda de marca.

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
pip install -e ".[api,lti]"
PYTHONPATH=src python -m unittest discover -s tests      # 108 pruebas; las de HTTP corren con FastAPI y httpx reales, y la integración PostgreSQL se ejecuta en CI
```

### PostgreSQL con aislamiento por escuela (opcional, requiere Docker Desktop)

```bash
docker compose -f deploy/docker-compose.db.yml up -d
python scripts/check_postgres.py --admin-url postgresql://postgres:cambiar@localhost:5432/matheval --app-url postgresql://matheval_app:cambiar-en-produccion@localhost:5432/matheval
```

Si venís de una versión anterior, SQLite aplica sus migraciones compatibles al arrancar. En PostgreSQL existente, ejecutá con el propietario de la base las migraciones pendientes en orden, desde `db/002_migracion_v05.sql` hasta `db/005_migracion_v10.sql` (sin repetir las que ya aplicaste). La migración `004` deja las membresías de red existentes como pendientes: cada escuela debe aceptar de nuevo antes de compartir agregados.

Cuando algo falle, anotá el comando, el mensaje de error completo y las versiones de Node y Python. Los puntos con más
riesgo son `smoke_http.py` (primera ejecución real de PyLTI1p3), `npm run dev` con las pantallas de revisión y,
si lo probás, `check_postgres.py`.

## Próximos pasos

1. Corregir lo que aparezca al montar el entorno (primera ronda de errores de instalación y de tipos).
2. Probar la persistencia en PostgreSQL con RLS (`DATABASE_URL=postgresql://...`) y ajustar lo que aparezca.
3. Corregir lo que muestre `smoke_http.py` en el ingreso por LTI; después probar con un Moodle real y ajustar el realm de Keycloak.
4. Más plantillas (N2, N7, N8), ítems con gráficos y flujo de revisión docente del banco.
5. Importación de ítems QTI con qti3-item-player y tablero docente por estudiante (con permisos y consentimiento).
6. Piloto en una o dos escuelas, calibración con `calibration.py` y estudio de puntos de corte.

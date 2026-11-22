# Análisis de funcionalidades: qué se incorporó y qué sigue

La plataforma no es solo un lugar para resolver ejercicios: combina práctica adaptativa, medición, **observatorio de resultados históricos**, **tendencias en el tiempo** y vistas para docentes, escuelas y redes. Esta página resume cómo se reparte cada pieza.

Criterio de selección: valor para el aprendizaje y para el docente, riesgo (sobre todo privacidad de menores y
cumplimiento), esfuerzo y posibilidad de verificarlo. El CI actual incluye pruebas Python/HTTP, PostgreSQL 16,
PyLTI1p3 contra un LMS simulado, Playwright/axe en Chromium y un recorrido integral del stack local de Docker Compose.
Los servicios institucionales/productivos y la revisión manual siguen pendientes.

## Incorporado en la versión 0.8: respuestas abiertas y corrección docente

| Funcionalidad | Por qué | Estado |
|---|---|---|
| Actividades de respuesta abierta creadas por docentes a partir del banco | Permite evaluar razonamiento, argumentación y procedimientos que no se reducen a una opción múltiple | Flujo implementado en API y web; asignación por escuela o curso disponible en la interfaz docente |
| Reentregas e historial de intentos | Permite revisar la devolución docente, mejorar una respuesta y conservar la evolución de cada intento | Se habilita un nuevo intento solo después de corregir el anterior; cada versión y su calificación permanecen consultables por el estudiante y el docente |
| Cancelación de actividades abiertas | Permite retirar una consigna por cambios de calendario sin borrar evidencias ya entregadas | El docente cancela una sola vez; el servidor bloquea nuevos intentos y conserva entregas, calificaciones e historial. El motivo es visible para los estudiantes |
| Entrega única por estudiante y actividad, con aislamiento por escuela | Evita duplicados y cruces de datos entre instituciones | Restricción única, RLS y pruebas SQLite/PostgreSQL 16 |
| Corrección manual con puntuación y devolución escrita | Hace visible el razonamiento y permite retroalimentación formativa | Implementado; la puntuación y el comentario quedan vinculados a la entrega |
| Rúbricas orientativas por competencia (15 habilidades del mapa Q) | Alinea la devolución con la habilidad que el docente quiere observar | Biblioteca inicial con tres criterios y descriptores 0–4; la asignación conserva una copia inmutable de la rúbrica usada |
| Validación de la corrección contra la rúbrica asignada | Evita guardar criterios inventados o incompletos en actividades con rúbrica competencial | API exige puntuar todos los criterios con valores enteros 0–4; cobertura SQLite, HTTP y PostgreSQL 16 |
| Consulta de entregas y devolución al estudiante | Cierra el ciclo entre consigna, respuesta y retroalimentación | Implementado; el estudiante ve el estado, la puntuación y los descriptores correspondientes a su corrección |
| Supresión de entregas abiertas junto con los datos locales del estudiante | Mantiene coherencia con el derecho de supresión | Incluido en el flujo de borrado y probado en PostgreSQL 16 |
| Identificación de entregas mediante seudónimo | Evita exponer nombres personales en la plataforma | El identificador persistido es un seudónimo; si el LMS ofrece NRPS, el docente ve el nombre en vivo sin guardarlo en Matheval |
| Consulta de roster LTI NRPS de solo lectura | Permite que el docente reconozca a sus estudiantes sin mantener una copia local del padrón | Implementado con LMS simulado; requiere scope NRPS y allowlist del host en el registro real; si no está disponible, se conserva el seudónimo |

**Operación:** en PostgreSQL existente hay que aplicar `db/014_migracion_v19.sql` y `db/015_migracion_v20.sql` antes de desplegar esta versión; la primera copia las entregas previas como intento 1 y habilita RLS, y la segunda añade metadatos de cancelación. El Compose monta ambas migraciones para bases nuevas. **Límites actuales:** no hay avisos automáticos de vencimiento. El motivo de cancelación se muestra al alumnado; no debe incluir datos personales ni información sensible. Los intentos se conservan por separado; la API muestra los 50 más recientes en el historial. Las actividades admiten fecha y hora límite con zona horaria: el servidor valida el dato, informa si venció y bloquea de forma atómica las entregas tardías. La biblioteca inicial ofrece rúbricas orientativas para las 15 habilidades del mapa Q, con descriptores de nivel 0–4 y copia inmutable por actividad. Los descriptores son formativos y genéricos: requieren validación curricular con docentes antes de considerarse una escala estandarizada o de usarse para decisiones de alto impacto. Los nombres del roster NRPS se consultan en tiempo real y solo se muestran al docente autorizado; no se almacenan. El LMS real debe habilitar el scope NRPS y registrar sus hosts permitidos; la integración se valida en CI contra un LMS simulado, no contra una instancia institucional. El flujo no forma parte del motor adaptativo ni de la calibración psicométrica.

## Incorporado en la versión 0.7: microdatos de PISA, errores estándar y brechas

| Funcionalidad | Por qué | Estado |
|---|---|---|
| Motor estadístico de PISA: replicación BRR con ajuste de Fay y valores plausibles | Sin errores estándar no se puede decir si un cambio es real o ruido | Probado con simulaciones (el error estándar coincide con la variación real entre muestras) |
| Brechas por cuartil de ESCS, por género y gradiente socioeconómico | Muestra la desigualdad detrás del promedio | Probado con archivos simulados en el formato de PISA |
| Carga desde los microdatos oficiales (`scripts/pisa_ingest.py`) con conciliación contra lo publicado | Evita errores de país, ciclo o columnas | Probado con datos simulados; **falta correrlo con un archivo real de la OCDE** |
| Bandas de confianza y pruebas de cambio entre ciclos en el observatorio | Interpretación honesta de las tendencias | API probada; pantalla pendiente de navegador |
| Panel de brechas del observatorio | Equidad a simple vista | Pendiente de navegador y de datos reales |

## Incorporado en la versión 0.6: observatorio, tendencias y vistas de red

| Funcionalidad | Por qué | Estado |
|---|---|---|
| Observatorio de resultados de PISA 2000-2025 (matemática, lectura y ciencias) con procedencia por dato | Es la parte «datos históricos globales» de la idea original: contexto para escuelas y gobiernos | Datos y cálculos probados; pantallas pendientes de navegador |
| Evolución, comparación entre países, brecha con la OCDE, promedio regional y % bajo el nivel 2 | Permite ver tendencias de Argentina frente a la región y a países de referencia | Probado |
| Registro de calidad de cada dato (oficial u secundaria) y avisos de límites | Evita presentar como firme lo que no lo es: no se declara significancia sin errores estándar | Probado |
| Tendencias mensuales de la escuela o del curso (nivel promedio y % que alcanza el mínimo) | Muestra el progreso real de las prácticas en el tiempo | Probado en la API |
| «Mi evolución» del estudiante | Línea de tiempo de sus niveles | Pendiente de navegador |
| Vista de red o jurisdicción con supresión de celdas de menos de 10 estudiantes | Cubre la necesidad de gobiernos y redes sin exponer escuelas chicas ni permitir deducciones por diferencia | API y Playwright/axe; PostgreSQL RLS, invitación, aceptación y revocación probados |
| Informe de la escuela para imprimir o guardar como PDF | Entrega un documento listo para reuniones | Pendiente de navegador |

## Incorporado en la versión 0.5

| Funcionalidad | Por qué | Estado |
|---|---|---|
| 15 habilidades con prerrequisitos y mapa plantilla-habilidad | Sin esto no hay rutas de aprendizaje: la medición dice «dónde estás», las habilidades dicen «qué practicar» | Probado |
| Dominio por habilidad (seguimiento bayesiano de conocimiento) | Estima qué domina cada estudiante; las respuestas con pista no suman evidencia | Probado |
| Práctica dirigida por tema con ejercicios espejo | Tras un error se ofrece otra instancia de la misma plantilla; dos errores seguidos bajan la dificultad; los aciertos la suben | Probado |
| Pistas (2 niveles) y resolución paso a paso | Devolución inmediata y formativa; cada resolución se autoverifica contra la clave en las pruebas | Probado |
| Repaso espaciado y recomendaciones («qué practicar hoy») | Combina lo nuevo, lo débil y lo vencido, respetando prerrequisitos | Probado |
| 12 plantillas nuevas (total 24): gráficos de barras y líneas, figuras, promedio y mediana, sistemas, Pitágoras, interés, escalas | Más cobertura de contenido y de niveles; los ítems visuales se parecen más a las pruebas internacionales | Generación probada; dibujo en la web pendiente de ver en navegador |
| Modo piloto (una instancia por plantilla) | Recoge datos balanceados para calibrar | Probado |
| Calibración por familia de ítems (EM 2PL en formato largo) | Los ítems clonados comparten parámetros: se calibra por plantilla con unos cientos de respuestas, no por cada ítem | Probado con datos simulados |
| Análisis clásico por plantilla (dificultad, discriminación, tiempos, errores frecuentes, avisos) | Detecta plantillas defectuosas antes de que midan | Probado |
| Devolución de notas al libro de calificaciones del LMS (LTI Advantage, AGS) | Los docentes ya trabajan en el LMS; así ven nombres sin que la plataforma los guarde | PyLTI1p3 real probado en CI contra LMS simulado; Moodle real pendiente |
| Cursos (contexto LTI) y panel docente por curso | Un docente quiere ver su curso, no toda la escuela | Probado en la API |
| Panel docente: errores frecuentes, dominio por tema, exportación CSV | Convierte datos en decisiones de aula | API probada; panel base cubierto por Playwright/axe en Chromium |
| Confirmación de consentimiento por la escuela (condición para practicar), supresión local, retención y auditoría | Menores de edad: la institución es responsable y la plataforma debe permitir borrar | Borrado local y anonimización de auditoría probados; si hay LRS externo, el API devuelve 202 y exige supresión administrativa del proveedor |
| Reintentos idempotentes, control optimista de concurrencia, límites de frecuencia, métricas e ID de solicitud | Conexiones inestables, respuestas simultáneas y abuso | Pruebas API, SQLite y PostgreSQL 16; una respuesta concurrente gana y la otra se reconoce como duplicada o recibe conflicto sin sobrescribir el estado |
| Accesibilidad: tamaño de texto, alto contraste, lectura en voz alta, tablas alternativas a los gráficos | Inclusión y legibilidad | Login, práctica, docente, curaduría y red pasan axe en Chromium; faltan lectores de pantalla y revisión manual |
| Progreso del estudiante: temas, historial y recomendaciones | Motivación basada en dominio, sin rankings | API probada; pantalla pendiente |

## Evaluado y no incorporado

- **Rankings y tablas de líderes entre estudiantes:** exponen a menores y la evidencia sobre su efecto es mixta.
- **Chat libre del estudiante con un modelo de lenguaje:** exige salvaguardas para menores (verificación de edad,
  moderación, supervisión). La IA se usa solo para proponer contextos que revisa un docente.
- **Vigilancia de examen (proctoring) y bloqueo del navegador:** no corresponden a una práctica formativa.
- **Usar respuestas de estudiantes para entrenar modelos:** no, por contrato y por diseño.

## Propuestas siguientes, en orden sugerido

0. **Cargar los microdatos reales de PISA** (ARG y países de referencia) y sumar los errores de vinculación publicados por la OCDE.
1. **Estudio de puntos de corte** (por ejemplo Angoff o marcador) para fijar los niveles N1 a N8 con docentes y datos del piloto.
2. **Más plantillas y variedad de contextos revisados** (hoy hay una por habilidad en varios niveles); banco de contextos regionales.
3. **LTI Deep Linking y NRPS:** elegir la actividad dentro del LMS y listar el curso sin guardar nombres.
4. **Modo medición adaptativo con CAT** una vez calibrado el banco, con control de exposición.
5. **Aplicación instalable con modo de conexión limitada** (service worker y cola local de respuestas).
6. **Respuestas abiertas con rúbrica** y corrección asistida con revisión docente.
7. **Teclado matemático** para escribir expresiones (por ejemplo MathLive, verificando su licencia) e interactivos para N7 y N8.
8. **Análisis de funcionamiento diferencial de ítems** por grupos: requiere un diseño de consentimiento y de agregación específico.
9. **Reportes en PDF** para familias, gestionados por la escuela.
10. **Operación:** copias de respaldo, panel de métricas (Prometheus y Grafana), alta disponibilidad y pruebas de carga.

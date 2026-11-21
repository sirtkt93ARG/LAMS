# Análisis de funcionalidades: qué se incorporó y qué sigue

La plataforma no es solo un lugar para resolver ejercicios: combina práctica adaptativa, medición, **observatorio de resultados históricos**, **tendencias en el tiempo** y vistas para docentes, escuelas y redes. Esta página resume cómo se reparte cada pieza.

Criterio de selección: valor para el aprendizaje y para el docente, riesgo (sobre todo privacidad de menores y
cumplimiento), esfuerzo y posibilidad de verificarlo. El CI actual incluye pruebas Python/HTTP, PostgreSQL 16, PyLTI1p3
contra un LMS simulado y Playwright/axe en Chromium. Los servicios productivos y la revisión manual siguen pendientes.

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
| Confirmación de consentimiento por la escuela (condición para practicar), supresión de datos, retención y auditoría | Menores de edad: la institución es responsable y la plataforma debe permitir borrar | Probado |
| Reintentos idempotentes, límites de frecuencia, métricas y ID de solicitud | Conexiones inestables y abuso; PISA 2025 se entregó también sin conexión | Probado en la API |
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

# Auditoría de la plataforma (base histórica v0.7) e ideas para ampliarla

**Actualización de validación: 21-11-2026.** Esta página conserva hallazgos y mediciones históricas de la auditoría v0.7; no deben
interpretarse como una nueva medición estadística. Desde entonces se integraron correcciones de seguridad y gobernanza, pruebas PostgreSQL
16 con RLS, un recorrido LTI 1.3 real con PyLTI1p3 contra el LMS simulado y ocho pruebas Playwright/axe en Chromium. La validación actual
se ejecuta en GitHub Actions. El stack local de Docker Compose ya pasa el smoke test integral; siguen pendientes la operación productiva,
Moodle real, Keycloak institucional, LRS xAPI y pruebas manuales con tecnologías de asistencia.

Las cifras de exposición, diversidad y simulación que aparecen más abajo son históricas. Repetilas antes de citarlas en material externo.

## 1. Veredicto

La plataforma ya cuenta con pruebas automatizadas de núcleo, API y HTTP; integración PostgreSQL 16; smoke LTI 1.3 con PyLTI1p3
contra el LMS simulado; y ocho pruebas de navegador con axe. Los principales frentes pendientes son **operación productiva** (backups, restauración, monitoreo, Keycloak institucional
y Moodle real), **validación educativa** (calibración con un piloto y análisis con microdatos PISA) y **accesibilidad
manual** (lectores de pantalla, Firefox/WebKit y dispositivos reales).

## 2. Hallazgos con evidencia

Estado: situación en la rama `main` a 21-11-2026. Los valores numéricos de evidencia son históricos; no se recalcularon en esta actualización.

| # | Hallazgo | Evidencia | Estado |
|---|---|---|---|
| 1 | **Todos los estudiantes reciben casi el mismo examen.** El armado de bloques era determinista | El bloque inicial era idéntico en sesiones distintas y solo se usaban 56 de 400 ejercicios del banco (14 %), todos vistos por más de la mitad de los estudiantes. Con sorteo entre los 16 más cercanos: exposición máxima 37 %, 70 % del banco usado, ningún ejercicio visto por más del 50 %, a cambio de un error de medición un poco mayor (de 0,355 a 0,393) | Corregido en el motor actual; simulaciones históricas, falta repetir medición de exposición y variedad |
| 2 | **Poca variedad real de contenido.** Hay muchas semillas pero pocas variantes | De 4.800 ejercicios generados solo 2.090 (44 %) eran distintos; la plantilla T12 tenía 4 variantes, T22 tenía 8 y T10 tenía 10. El «ejercicio espejo» podía ser exactamente el mismo que el fallado. Tras ampliar parámetros: 3.658 distintos de 4.800 (76 %); banco sin duplicados de 3.966 ejercicios | Corregido: suite actual ejecutada en CI |
| 3 | **Cualquier docente de cualquier escuela puede aprobar o rechazar plantillas para todas las escuelas**, y un rechazo no se puede revertir | Un solo docente de otra escuela dejó rechazada la plantilla T5 para todos | Corregido: API y pruebas HTTP restringen la curaduría al rol admin; browser test incluido |
| 4 | **El token de traspaso LTI se describe «de un solo uso» pero se podía reutilizar** durante sus 60 segundos | El mismo token se canjeó tres veces seguidas | Corregido: JTI de un solo uso; prueba de integración PostgreSQL |
| 5 | **Secretos por defecto**: con `PSEUDONYM_SECRET` sin definir, los seudónimos de los estudiantes se pueden reproducir | El valor por defecto es público; docker-compose también usa valores de ejemplo | Corregido: configuración de producción valida secretos y orígenes |
| 6 | **Respuestas duplicadas con solicitudes simultáneas** sobre la misma sesión | Dos solicitudes que leen el mismo estado podían guardar el mismo ejercicio dos veces | Corregido: control optimista de versión, actualización del estado e inserción de respuesta en una sola transacción, índice único y pruebas concurrentes SQLite/PostgreSQL |
| 7 | **Una red podía agregar a cualquier escuela** conociendo su identificador y ver sus resultados agregados | La invitación no necesitaba aceptación | Corregido: invitación, aceptación y revocación de consentimiento; RLS y pruebas PostgreSQL |
| 8 | **Colores con poco contraste**: los celestes y ámbar de los gráficos quedaban por debajo de 3:1 y las etiquetas de línea coloreadas por debajo de 4,5:1 | Celeste #56B4E9 ≈ 2,3:1 y ámbar #E69F00 ≈ 2,3:1 sobre blanco | Corregido: paleta de mayor contraste; axe no detectó violaciones en los recorridos cubiertos |
| 9 | **Pruebas frágiles**: dependían del orden de importación (`importlib.util`) | La suite fallaba al descubrir las pruebas en otro orden | Corregido: suite actual ejecutada en CI |
| 10 | **Ítems abiertos sin flujo de corrección manual** podían entrar en pools automáticos y afectar la estimación de nivel | El motor admite `kind=open`, cuya puntuación es `None`; una práctica automática no debe convertirla silenciosamente en incorrecta | Corregido parcialmente: excluidos de pools adaptativos y rechazados en API; falta construir rúbricas y corrección docente |

## 3. Hallazgos abiertos (sin arreglo)

| Tema | Detalle | Recomendación |
|---|---|---|
| Estado en memoria por proceso | Las decisiones de curaduría persisten en la base y cada worker las vuelve a aplicar antes de crear sesiones. El rate limiting ahora usa contadores atómicos en PostgreSQL/SQLite, compartidos entre workers; los contadores de métricas siguen siendo locales al proceso | Centralizar métricas para escalar horizontalmente; desplegar la migración v16 antes de actualizar instancias existentes |
| Supresión externa pendiente | `DELETE /v1/me/data` elimina sesiones/respuestas locales y anonimiza los eventos de auditoría del actor; si `LRS_URL` está configurado, devuelve 202 y el agente xAPI que requiere supresión manual | Integrar el mecanismo administrativo del LRS elegido; xAPI 1.0.3 solo define voiding, que no destruye Statements |
| Verificación de interfaz | Ocho pruebas Playwright/axe cubren login, práctica, panel docente, curaduría, red, teclado y viewport móvil en Chromium | Ampliar a Firefox/WebKit, lectores de pantalla y pruebas manuales con usuarios |
| Contenido | El proceso «argumentar» no tiene cobertura suficiente. Existe el tipo de ítem `open`, pero aún no hay flujo completo de corrección manual; por eso se excluye de los pools adaptativos automáticos. Varias habilidades tienen un solo nivel | Más plantillas, rúbricas y flujo de revisión docente para respuestas abiertas |
| Sesgo en porcentajes | El porcentaje de estudiantes por debajo de N4 sale 2 a 3 puntos más bajo en cohortes de bajo desempeño (se estimó 70,5 % con 72,6 % real; 92,2 % con 94,8 %). Promediar probabilidades posteriores no lo corrige | Prior por curso (Bayes empírico) o intervalos de incertidumbre |
| Escala | Iniciar una práctica recorre todo el banco y el dominio por tema recalcula desde las respuestas | Cachear el diseño y guardar el dominio de forma incremental antes de pasar de unos miles de respuestas |
| Cobertura | La cobertura histórica de 90,6 % corresponde a la suite v0.7 y no se recalculó. CI actual añade HTTP, PostgreSQL 16 y ocho pruebas de navegador con axe | Recalcular cobertura global y ampliar E2E a reportes, progreso y observatorio |

## 3 bis. Salud y disponibilidad

| Operación de API | `/healthz` verifica que el proceso responde; `/readyz` comprueba además conectividad real con la base y devuelve 503 si falla. Compose usa readiness para marcar la API saludable | Configurar el balanceador/orquestador productivo para retirar instancias no listas; definir monitoreo y alertas |

## 4. Lo que mostraron las simulaciones (valores aproximados)

- **Tamaño del piloto:** con 100 estudiantes por familia de ítems el error de dificultad es de unos 0,5; con 300, de 0,22 (81 % dentro de ±0,25); con 800, de 0,13 (94 %). La plataforma usa 300 como mínimo: sirve para práctica; para medir conviene 500 a 800.
- **Diseño multietapa:** supera a una forma fija solo si las dificultades supuestas son razonables. Con dificultades equivocadas por 0,9 desvíos la ventaja desaparece. Los umbrales de ruteo casi no importan (el error varía entre 0,43 y 0,44): la ganancia viene de centrar el examen en la cohorte. **Hay que calibrar antes de medir.**
- **Práctica por tema:** la escalera de dificultad solo puede moverse entre los niveles que tiene cada habilidad. En habilidades con niveles altos (por ejemplo funciones lineales) los estudiantes de menor nivel aciertan muy poco (cerca de 12 %), y los más avanzados no encuentran desafío. Hacen falta ejercicios fáciles de entrada y difíciles de techo en cada habilidad.
- **Estimador de dominio (BKT):** robusto a errores en la tasa de aprendizaje (85 a 88 % de exactitud al clasificar «domina»), sensible a errores en la tasa de error y de adivinar (77 %): conviene calibrar esos parámetros con datos.
- **Precisión por curso:** el error de medición por estudiante es de unos 0,6 niveles; para que el promedio de un curso tenga error estándar de 0,3 niveles hacen falta unos 21 estudiantes, y para 0,2, unos 46.
- **Contraste:** véase el hallazgo 8.

## 5. Qué se le puede agregar

Ideas ordenadas por eje. Todo está en estado de propuesta; esfuerzo y valor son estimaciones propias.

### Control y gobernanza
1. **Panel de calidad del banco:** alertas de plantillas muy fáciles, muy difíciles o que discriminan poco (ya existe el análisis por escuela; falta el panel global para curadores).
2. **Versionado de plantillas:** un cambio invalida la calibración; registrar versión y fecha.
3. **Consola de administración:** roles, escuelas, retención por escuela, exportación de auditoría.
4. **Salud y operación:** métricas y alertas, copias de respaldo, pruebas de carga, estado de cada integración (LTI, xAPI, base).
5. **Gestión del consentimiento** con evidencia (fecha, quién, versión del aviso) y política de retención configurable.

### Análisis
6. **Estudio de puntos de corte** (Angoff o marcador) para fijar los niveles N1 a N8.
7. **Vinculación de pruebas y error de vinculación** para comparar ciclos propios y con PISA.
8. **Crecimiento individual y de curso** (percentiles de crecimiento) con intervalos y advertencias sobre valor agregado.
9. **Alerta temprana** para docentes basada en dominio y tendencia, con auditoría de equidad antes de usarla.
10. **Funcionamiento diferencial de ítems** por grupo, con diseño de consentimiento y agregación.
11. **Análisis de tiempos de respuesta** (adivinanza rápida, fatiga).
12. **Mapa de errores frecuentes** (qué errores aparecen juntos) y alineación con el currículo (mapa de cobertura de NAP).
13. **Simulador de políticas** con datos de PISA: «si el cuartil más bajo mejora X puntos, qué pasa con el porcentaje bajo el nivel 2».

### Desarrollo del aprendizaje
14. **Más contenido:** plantillas fáciles de entrada y difíciles de techo por habilidad, ejercicios de «argumentar» y respuestas abiertas con rúbrica y corrección asistida con revisión docente, más contextos regionales.
15. **Rutas por prerrequisitos:** si falla en una habilidad, ofrecer su prerrequisito; visualizar el grafo.
16. **Tareas del docente:** asignar práctica por tema a un curso con fecha.
17. **Metas y autorregulación:** metas semanales privadas y reflexión breve después de cada práctica.
18. **Ejemplos resueltos que se van retirando** (fading) y práctica intercalada y espaciada ya medida con datos.
19. **Aplicación instalable con modo de conexión limitada** y teclado matemático (por ejemplo MathLive, verificando su licencia).
20. **Material para el docente:** sugerencias de actividades por tipo de error con recursos abiertos de licencia verificada.

### Laboratorio de simulación (propuesta de módulo)
Un conjunto de scripts y una pantalla para curadores que respondan antes de decidir: tamaño del piloto, diseño del examen
(forma fija, multietapa o adaptativo), exposición de ítems, efecto de dificultades mal calibradas, aprendizaje simulado para probar
políticas de repaso, tamaño de muestra por escuela, sesgo de las estimaciones agregadas y capacidad del sistema.

## 6. Límites de esta auditoría

- **Navegador:** ocho recorridos Playwright/axe corren en Chromium sobre el servidor Next.js de producción. No sustituyen pruebas manuales, lectores de pantalla ni Firefox/WebKit.
- **LTI:** PyLTI1p3 real y devolución AGS se ejecutan contra un LMS simulado; Moodle real y Keycloak de producción no se han probado.
- **PostgreSQL y Compose:** esquema, migraciones y RLS se prueban con PostgreSQL 16 efímero en CI. El stack local de Docker Compose también pasa el recorrido HTTP/LTI completo, incluida la devolución AGS. Esto no valida backups, restauración, monitoreo ni operación productiva.
- **xAPI:** el LRS Ralph no se ha ejecutado ni validado con un servidor real.
- **Datos del observatorio:** las medias 2000 a 2022 se transcribieron a mano de las tablas de la OCDE; el promedio de tendencia, todo PISA 2025 y los porcentajes bajo el nivel 2
  son de fuentes secundarias. Hace falta contrastarlos con las tablas oficiales.
- **Microdatos de PISA:** el motor estadístico se validó con simulaciones; falta correrlo con un archivo real.
- **Sin revisión legal profesional:** licencias (TAO, dependencias), consentimiento, contratos de encargo de datos, marca y uso de ítems de PISA requieren abogado.
- **Los scripts de medición se perdieron** con el reinicio del entorno y las cifras de la sección 4 son aproximadas.

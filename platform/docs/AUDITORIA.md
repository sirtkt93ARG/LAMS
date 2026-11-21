# Auditoría de la plataforma (sobre la versión 0.7) e ideas para ampliarla

Qué se revisó y cómo: se midió con código en lugar de suponer. Cobertura de pruebas, sondas de seguridad y gobernanza,
simulaciones del motor, variedad y cobertura del contenido, contraste de colores y rendimiento. **Aviso:** esas mediciones se hicieron
en una copia de trabajo y los scripts se perdieron cuando se reinició el entorno. Las cifras de esta página son las que se registraron
en ese momento; repetilas antes de citarlas en material externo. Lo que no se pudo verificar está en el último apartado.

## 1. Veredicto

La plataforma funciona de punta a punta en pruebas automáticas (91 pruebas del núcleo y de la lógica de la API) y su parte
estadística está validada con simulaciones. Antes de usarla con estudiantes reales hay que cerrar cuatro frentes: **seguridad y
gobernanza** (hallazgos 3 a 7), **seguridad del examen** (hallazgos 1 y 2), **verificación en navegador** (nunca se vio la web
en un navegador desde la v0.2) y **datos reales** (calibración con un piloto y microdatos de PISA).

## 2. Hallazgos con evidencia

Estado: «parche» significa que existe un arreglo en `docs/arreglos_auditoria/` que no está aplicado en este paquete.

| # | Hallazgo | Evidencia | Estado |
|---|---|---|---|
| 1 | **Todos los estudiantes reciben casi el mismo examen.** El armado de bloques era determinista | El bloque inicial era idéntico en sesiones distintas y solo se usaban 56 de 400 ejercicios del banco (14 %), todos vistos por más de la mitad de los estudiantes. Con sorteo entre los 16 más cercanos: exposición máxima 37 %, 70 % del banco usado, ningún ejercicio visto por más del 50 %, a cambio de un error de medición un poco mayor (de 0,355 a 0,393) | Parche A |
| 2 | **Poca variedad real de contenido.** Hay muchas semillas pero pocas variantes | De 4.800 ejercicios generados solo 2.090 (44 %) eran distintos; la plantilla T12 tenía 4 variantes, T22 tenía 8 y T10 tenía 10. El «ejercicio espejo» podía ser exactamente el mismo que el fallado. Tras ampliar parámetros: 3.658 distintos de 4.800 (76 %); banco sin duplicados de 3.966 ejercicios | Parche A |
| 3 | **Cualquier docente de cualquier escuela puede aprobar o rechazar plantillas para todas las escuelas**, y un rechazo no se puede revertir | Un solo docente de otra escuela dejó rechazada la plantilla T5 para todos | Parche B (solo rol curador) |
| 4 | **El token de traspaso LTI se describe «de un solo uso» pero se podía reutilizar** durante sus 60 segundos | El mismo token se canjeó tres veces seguidas | Parche B |
| 5 | **Secretos por defecto**: con `PSEUDONYM_SECRET` sin definir, los seudónimos de los estudiantes se pueden reproducir | El valor por defecto es público; docker-compose también usa valores de ejemplo | Parche B (la API se niega a arrancar fuera de desarrollo) |
| 6 | **Respuestas duplicadas con solicitudes simultáneas** sobre la misma sesión | Dos solicitudes que leen el mismo estado dejaron el mismo ejercicio registrado dos veces | Parche B (índice único) |
| 7 | **Una red podía agregar a cualquier escuela** conociendo su identificador y ver sus resultados agregados | La invitación no necesitaba aceptación | Parche B (invitaciones que la escuela acepta) |
| 8 | **Colores con poco contraste**: los celestes y ámbar de los gráficos quedaban por debajo de 3:1 y las etiquetas de línea coloreadas por debajo de 4,5:1 | Celeste #56B4E9 ≈ 2,3:1 y ámbar #E69F00 ≈ 2,3:1 sobre blanco | Hecho en la web del parche (paleta nueva, etiquetas en texto oscuro): hay que reaplicarlo |
| 9 | **Pruebas frágiles**: dependían del orden de importación (`importlib.util`) | La suite fallaba al descubrir las pruebas en otro orden | Parche A |

## 3. Hallazgos abiertos (sin arreglo)

| Tema | Detalle | Recomendación |
|---|---|---|
| Estado en memoria por proceso | El límite de frecuencia, las métricas y las revisiones aprobadas viven en la memoria de cada proceso | Ejecutar un solo proceso o mover ese estado a Redis o a la base |
| Borrado incompleto | `DELETE /v1/me/data` no borra lo enviado al almacén de xAPI (Ralph); la auditoría y las revisiones guardan el identificador del docente sin seudonimizar | Agregar el borrado en el LRS y seudonimizar docentes |
| Sin bloqueo optimista | Con dos solicitudes simultáneas, la última escritura pisa el estado | Columna de versión en la sesión |
| Web sin verificación en navegador | Solo hay 4 pruebas automáticas de librerías; las páginas se revisaron con TypeScript contra declaraciones mínimas | Instalar, correr `npm run typecheck`, `next build` y pruebas con Playwright y axe |
| Contenido | El proceso «argumentar» del marco no tiene ningún ejercicio; no hay respuestas abiertas; varias habilidades tienen un solo nivel, así que la práctica por tema no puede adaptarse | Más plantillas (ver propuestas) |
| Sesgo en porcentajes | El porcentaje de estudiantes por debajo de N4 sale 2 a 3 puntos más bajo en cohortes de bajo desempeño (se estimó 70,5 % con 72,6 % real; 92,2 % con 94,8 %). Promediar probabilidades posteriores no lo corrige | Prior por curso (Bayes empírico) o intervalos de incertidumbre |
| Escala | Iniciar una práctica recorre todo el banco y el dominio por tema recalcula desde las respuestas | Cachear el diseño y guardar el dominio de forma incremental antes de pasar de unos miles de respuestas |
| Cobertura | 90,6 % de las líneas de Python con las 91 pruebas (la medición subestima dos archivos); 0 % automatizado en pantallas | Pruebas de integración en navegador |

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

- **No se vio ninguna pantalla en un navegador**; todo lo de la web se revisó con TypeScript contra declaraciones mínimas.
- **PyLTI1p3 real, PostgreSQL, Docker, Keycloak y el almacén de xAPI no se ejecutaron**; el ingreso LTI y la devolución de notas se
  probaron con sustitutos y con un aula virtual simulada.
- **Datos del observatorio:** las medias 2000 a 2022 se transcribieron a mano de las tablas de la OCDE; el promedio de tendencia, todo PISA 2025 y los porcentajes bajo el nivel 2
  son de fuentes secundarias. Hace falta contrastarlos con las tablas oficiales.
- **Microdatos de PISA:** el motor estadístico se validó con simulaciones; falta correrlo con un archivo real.
- **Sin revisión legal profesional:** licencias (TAO, dependencias), consentimiento, contratos de encargo de datos, marca y uso de ítems de PISA requieren abogado.
- **Los scripts de medición se perdieron** con el reinicio del entorno y las cifras de la sección 4 son aproximadas.

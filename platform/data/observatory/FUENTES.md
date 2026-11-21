# Fuentes del observatorio PISA

Este archivo documenta la procedencia de los datos incluidos en `pisa_agregados.csv`.
La clasificación de calidad se conserva por fila en el propio CSV.

## Resultados PISA 2000–2022

- **Fuente principal:** OCDE, *PISA 2022 Results (Volume I)*, Anexo D, «Snapshot of mathematics, reading and science results».
- **URL:** https://www.oecd.org/en/publications/pisa-2022-results-volume-i_53f23881-en/full-report/component-29.html
- Las filas procedentes de esta tabla se identifican como `oficial_ocde`.
- Para Argentina 2022 se incluye una nota sobre el cambio de evaluación en papel a computadora.

## Promedio OCDE de tendencia

- **Fuente secundaria:** datos referenciados por data.gov.uk y EMS Magazine 133 (2024).
- **URL:** https://social-mobility.data.gov.uk/drivers_of_social_mobility/educational_opportunities_and_quality_of_schooling/availability-of-high-quality-school-education
- No representa necesariamente el promedio OCDE publicado para cada ciclo: es un promedio de países con datos comparables en todos los ciclos. El CSV lo advierte en la columna `nota` y clasifica estas filas como `secundaria`.

## Datos atribuidos a PISA 2025

- **Fuente secundaria citada por el script de construcción:** Chequeado, nota sobre resultados PISA 2025.
- **URL:** https://chequeado.com/nota/pruebas-pisa-2025-8-de-cada-10-estudiantes-argentinos-no-alcanza-el-nivel-minimo-en-matematica-y-el-59-tampoco-en-lectura
- Estos valores y los porcentajes bajo el nivel 2 citados por prensa están marcados como `secundaria`. Deben contrastarse con las tablas oficiales de la OCDE antes de utilizarlos como resultados definitivos.

## Microdatos y cálculos propios

Los microdatos oficiales no se incluyen en el repositorio ni se redistribuyen. El procesamiento documentado en `docs/MICRODATOS_PISA.md` permite calcular agregados y errores estándar localmente. Las filas calculadas por el proyecto se identifican como `microdatos_propios` y deben conciliarse con las publicaciones oficiales.

## Advertencia de uso

La presencia de una URL y de una etiqueta de calidad no sustituye la verificación de cada cifra contra la tabla original. Antes de publicar o utilizar estos resultados para decisiones, revisar la fuente enlazada, las notas metodológicas y la comparabilidad entre ciclos.

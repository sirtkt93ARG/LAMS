# Microdatos de PISA: cómo cargar el observatorio con errores estándar y brechas

Con esto el observatorio pasa de «puntajes promedio» a **intervalos de confianza, pruebas de cambio entre ciclos y brechas
por nivel socioeconómico y género**, calculados como lo hace la OCDE.

## Qué se calcula y cómo

- **Errores estándar:** replicación balanceada repetida (BRR con ajuste de Fay de 0,5) con los 80 pesos de replicación, más la
  variabilidad entre los valores plausibles (reglas de Rubin). Está en `src/matheval/observatory/microdata.py` y se validó con
  simulaciones: el error estándar coincide con la dispersión real de la media entre muestras repetidas.
- **Resultados:** media por dominio, porcentaje bajo el nivel 2 y en los niveles 5 y 6 (matemática), medias por género y por
  cuartil de ESCS, brechas con su error estándar y el gradiente socioeconómico (puntos por unidad de ESCS).
- **Cambios entre ciclos:** se prueban con los errores estándar de cada ciclo. **No incluyen el error de vinculación** (link error)
  que la OCDE agrega al comparar ciclos; con él, algunos cambios dejan de ser significativos. La pantalla lo aclara.

## Pasos

1. Descargá el archivo de estudiantes del ciclo desde la página de datos de PISA de la OCDE (`oecd.org/pisa/data`; enumera el
   PISA Data Explorer, Education GPS y la base de datos). Hace falta el archivo con **todos los estudiantes, los valores plausibles
   y los pesos de replicación** (en SPSS, `.sav`). Leé antes los términos de uso de la OCDE.
2. Guardalo fuera del repositorio o en `data/raw/` (está en `.gitignore`). **No se redistribuye ni se sube a ningún servidor:**
   la plataforma conserva solo los agregados.
3. Instalá lo necesario: `pip install -e ".[microdata]"` (DuckDB, pandas y pyreadstat).
4. Ejecutá, por ciclo (código de país de PISA: `ARG`):

   ```bash
   python scripts/pisa_ingest.py --file data/raw/CY08MSP_STU_QQQ.sav --cycle 2022 --country ARG --entity Argentina
   ```

5. Mirá la **conciliación**: compara tu media calculada con la publicada en el CSV. Si la diferencia pasa de 2 puntos, dice
   «REVISAR» (país, ciclo o columnas equivocados). Después ejecutá `python scripts/validate_observatory.py`.
6. Repetí para cada ciclo y país. Las corridas repetidas actualizan filas, no las duplican.

## Ciclos anteriores a 2022

Los nombres de columnas cambian. Los valores por defecto son los de 2022. Para otros ciclos usá las opciones `--n-pv`
(5 valores plausibles antes de 2015, 10 desde 2015), `--weight-col`, `--rep-prefix` y `--gender-col`, **verificando los
nombres en el diccionario de datos de ese ciclo**. Los límites de niveles del código son los de matemática de PISA 2022
(redondeados; la OCDE publica los valores con dos decimales).

## Sobre `learningtower`

Es un paquete de **R** (no de Python, como decía el documento inicial) con licencia MIT que ofrece una versión simplificada de
los datos de 2000 a 2022. Sirve para explorar, pero su documentación describe un subconjunto de variables y un peso final del
estudiante; no encontré los pesos de replicación, así que **no alcanza para calcular errores estándar correctos**. Para eso se
usan los archivos oficiales.

## Privacidad y legalidad

- Los microdatos de PISA son anónimos, pero igual no se guardan en la plataforma ni se mezclan con datos de estudiantes de las escuelas.
- Citá siempre la fuente (OCDE, PISA) y revisá los términos de uso vigentes antes de publicar cualquier tabla derivada.
- Las filas calculadas se marcan `microdatos_propios` y la pantalla pide contrastarlas con las tablas oficiales.

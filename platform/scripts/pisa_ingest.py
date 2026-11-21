"""Calcula agregados con errores estándar de PISA a partir de los microdatos de la OCDE y completa el observatorio.
Antes de usarlo, descargá el archivo de estudiantes del ciclo desde la página de datos de la OCDE y leé sus términos de uso:
https://www.oecd.org/pisa/data/   (más detalles en docs/MICRODATOS_PISA.md)

Ejemplo:
  python scripts/pisa_ingest.py --file C:\\datos\\CY08MSP_STU_QQQ.sav --cycle 2022 --country ARG --entity Argentina
"""
import argparse, sys
sys.path.insert(0, "src")
from matheval.observatory.ingest import ColumnSpec, run

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--file", required=True, help="archivo de estudiantes (.sav, .csv o .parquet)")
ap.add_argument("--cycle", type=int, required=True)
ap.add_argument("--country", required=True, help="código de país de PISA (CNT), por ejemplo ARG")
ap.add_argument("--entity", required=True, help="nombre que se mostrará, por ejemplo Argentina")
ap.add_argument("--group", default="America Latina")
ap.add_argument("--domains", default="matematica,lectura,ciencias")
ap.add_argument("--n-pv", type=int, default=10, help="valores plausibles por dominio (10 desde 2015; 5 antes)")
ap.add_argument("--n-reps", type=int, default=80, help="pesos de replicación (80 en todos los ciclos)")
ap.add_argument("--gender-col", default="ST004D01T")
ap.add_argument("--weight-col", default="W_FSTUWT")
ap.add_argument("--rep-prefix", default="W_FSTURWT")
a = ap.parse_args()
spec = ColumnSpec(n_pv=a.n_pv, n_reps=a.n_reps, gender=a.gender_col, weight=a.weight_col, rep_prefix=a.rep_prefix)
report = run(a.file, a.cycle, a.country, a.entity, a.group, tuple(a.domains.split(",")), spec)
print(f"{'dominio':12s} {'calculada':>10s} {'error est.':>10s} {'publicada':>10s} {'diferencia':>11s}  conciliación")
for r in report:
    state = "OK" if r["conciliada"] else ("sin dato publicado" if r["publicada"] is None else "REVISAR (¿país, ciclo o columnas?)")
    print(f"{r['dominio']:12s} {r['calculada']:10.1f} {r['se']:10.2f} {str(r['publicada']):>10s} {str(r['diferencia']):>11s}  {state}")
print("\nListo: se actualizaron data/observatory/pisa_agregados.csv y data/observatory/pisa_brechas.csv")

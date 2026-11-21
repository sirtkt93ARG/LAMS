import sys
sys.path.insert(0, "src")
from matheval.observatory.data import load_csv, validate
rows = load_csv(sys.argv[1] if len(sys.argv) > 1 else "data/observatory/pisa_agregados.csv")
errs = validate(rows)
print(f"{len(rows)} observaciones;", "sin errores" if not errs else f"{len(errs)} errores")
for e in errs: print(" -", e)
sys.exit(1 if errs else 0)

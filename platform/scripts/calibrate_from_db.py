"""Calibra por familia de ítems (plantilla) con las respuestas guardadas y escribe data/calibration.json.
Uso (con el rol propietario de la base, que ve todas las escuelas):
  DATABASE_URL=sqlite:///data/matheval.db python scripts/calibrate_from_db.py [--min-obs 300]
También imprime el análisis clásico por plantilla (dificultad, discriminación, errores frecuentes)."""
import argparse, json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, "."); sys.path.insert(0, "src")
from api.app.store import Store
from matheval.analytics import family_stats
from matheval.bank import ItemBank
from matheval.calibration import calibrate_families

ap = argparse.ArgumentParser()
ap.add_argument("--min-obs", type=int, default=300)
ap.add_argument("--out", default="data/calibration.json")
a = ap.parse_args()
store = Store(os.getenv("DATABASE_URL", "sqlite:///data/matheval.db"))
bank = ItemBank.load(os.getenv("BANK_PATH", "data/bank_demo.jsonl"))
rows = store.tenant_rows(None)
fams = calibrate_families([(f"{r['tenant_id']}|{r['pid']}", r["item_id"], r["score"]) for r in rows if not r["hints"]], a.min_obs)
if not fams:
    sys.exit("No hay respuestas para calibrar.")
persons = len({(r["tenant_id"], r["pid"]) for r in rows})
json.dump({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "persons": persons, "min_obs": a.min_obs,
           "families": fams}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"{persons} personas, {len(rows)} respuestas. Calibración escrita en {a.out}\n")
print(f"{'Plantilla':10s} {'n':>6s} {'a':>6s} {'b':>6s}  listo")
for t, f in sorted(fams.items(), key=lambda kv: int(kv[0][1:])):
    print(f"{t:10s} {f['n_obs']:6d} {f['a']:6.2f} {f['b']:6.2f}  {'sí' if f['ok'] else 'no (faltan datos)'}")
print("\nAnálisis clásico:")
for s in family_stats(rows, bank.items):
    print(f"{s['template']:5s} n={s['n']:5d} p={s['p']} disc={s['discrimination']} errores={s['top_errors']} {','.join(s['flags'])}")

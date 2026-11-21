"""Borra sesiones y respuestas más viejas que N días (retención). Ejecutar con el rol propietario de la base.
Uso: DATABASE_URL=... python scripts/purge_old.py --days 365"""
import argparse, os, sys
sys.path.insert(0, ".")
from api.app.store import Store

ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=365); a = ap.parse_args()
n = Store(os.getenv("DATABASE_URL", "sqlite:///data/matheval.db")).purge_older_than(a.days)
print(f"Sesiones eliminadas (y sus respuestas): {n}")

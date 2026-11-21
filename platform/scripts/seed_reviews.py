"""SOLO DEMOSTRACIÓN: aprueba todas las plantillas como 'docente-demo' para probar el modo producción sin revisión
real. No sustituye la revisión docente."""
import os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "src")
from matheval import templates as T
from api.app.review import CHECKLIST, scope_of
from api.app.store import Store

store = Store(os.getenv("DATABASE_URL", "sqlite:///data/matheval.db"))
done = {r["scope"] for r in store.reviews() if r["reviewer"] == "docente-demo"}
for tid in T.SPEC:
    if scope_of(tid) not in done:
        store.add_review(scope_of(tid), "docente-demo", "aprobar", "Aprobación de demostración (no es una revisión real)",
                         {k: True for k in CHECKLIST})
print(f"Plantillas aprobadas de demostración: {len(T.SPEC)}. Recordá que no es una revisión real.")

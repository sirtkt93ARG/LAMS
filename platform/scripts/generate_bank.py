"""Genera un banco de demostración (estado 'verificado') y paquetes QTI 3 de muestra."""
import sys, pathlib
sys.path.insert(0, "src")
from matheval import templates as T
from matheval.bank import ItemBank
from matheval.qti3 import item_to_qti

N_PER_TEMPLATE, QTI_PER_TEMPLATE = 200, 20
bank = ItemBank()
out = pathlib.Path("data/qti"); out.mkdir(parents=True, exist_ok=True)
for stale in out.glob("*.xml"):
    stale.unlink()  # evita conservar QTI de semillas descartadas o de generaciones anteriores
for tid in T.SPEC:
    seen, seed, n = set(), 0, 0
    while n < N_PER_TEMPLATE and seed < 20 * N_PER_TEMPLATE:          # sin contenido repetido: se descartan semillas duplicadas
        it = T.generate(tid, seed)
        seed += 1
        if it.provenance["fp"] in seen:
            continue
        seen.add(it.provenance["fp"])
        bank.add(it)
        if n < QTI_PER_TEMPLATE:
            (out / f"{it.id}.xml").write_bytes(item_to_qti(it))
        n += 1
bank.dump("data/bank_demo.jsonl")
print(f"{len(bank.items)} ítems en data/bank_demo.jsonl; {len(T.SPEC) * QTI_PER_TEMPLATE} archivos QTI en data/qti/")

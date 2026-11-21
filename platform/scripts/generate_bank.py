"""Genera un banco de demostración (estado 'verificado') y paquetes QTI 3 de muestra."""
import sys, pathlib
sys.path.insert(0, "src")
from matheval import templates as T
from matheval.bank import ItemBank
from matheval.qti3 import item_to_qti

N_PER_TEMPLATE, QTI_PER_TEMPLATE = 200, 20
bank = ItemBank()
out = pathlib.Path("data/qti"); out.mkdir(parents=True, exist_ok=True)
for tid in T.SPEC:
    for seed in range(N_PER_TEMPLATE):
        it = T.generate(tid, seed)
        bank.add(it)
        if seed < QTI_PER_TEMPLATE:
            (out / f"{it.id}.xml").write_bytes(item_to_qti(it))
bank.dump("data/bank_demo.jsonl")
print(f"{len(bank.items)} ítems en data/bank_demo.jsonl; {len(T.SPEC) * QTI_PER_TEMPLATE} archivos QTI en data/qti/")

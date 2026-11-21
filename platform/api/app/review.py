"""Revisión docente por plantilla. Cada ítem se genera y se verifica con SymPy, así que la revisión humana
se hace sobre la plantilla (enunciado, contexto, distractores) con una muestra de instancias. Una plantilla
aprobada por la cantidad de revisores exigida pasa todos sus ítems 'verificado' a 'revisado'."""
from __future__ import annotations
import json
import os
from collections import defaultdict
from pathlib import Path
from matheval.bank import ItemBank
from matheval.models import IRTParams, Status
from .store import Store

REQUIRED = int(os.getenv("REVIEW_APPROVALS_REQUIRED", "1"))
CHECKLIST = ["clave_correcta", "enunciado_claro", "contexto_adecuado_15_anios", "distractores_plausibles", "sin_sesgos"]


def scope_of(tid: str) -> str:
    return f"template:{tid}"


def template_status(reviews: list[dict]) -> dict:
    ap = sum(1 for r in reviews if r["decision"] == "aprobar")
    rj = sum(1 for r in reviews if r["decision"] == "rechazar")
    status = "rechazada" if rj else ("aprobada" if ap >= REQUIRED else "pendiente")
    return {"status": status, "approvals": ap, "rejections": rj, "required": REQUIRED}


def apply_reviews(bank: ItemBank, store: Store) -> None:
    """Sincroniza el estado de los ítems del banco con las revisiones guardadas. Es idempotente."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in store.reviews():
        grouped[r["scope"]].append(r)
    for scope, revs in grouped.items():
        tid = scope.split(":", 1)[1]
        st = template_status(revs)["status"]
        names = ",".join(sorted({r["reviewer"] for r in revs if r["decision"] == "aprobar"}))
        for it in bank.items.values():
            if it.template != tid:
                continue
            if st == "rechazada" and it.status in (Status.VERIFICADO, Status.REVISADO):
                it.status = Status.RECHAZADO
            elif st == "aprobada" and it.status == Status.VERIFICADO:
                bank.promote(it.id, Status.REVISADO, reviewed_by=names)


def apply_calibration(bank: ItemBank, path: str | Path) -> int:
    """Aplica parámetros IRT por plantilla (data/calibration.json, generado por scripts/calibrate_from_db.py) y pasa a
    'calibrado' los ítems aprobados de las plantillas con datos suficientes. Devuelve cuántos ítems se calibraron."""
    p = Path(path)
    if not p.exists():
        return 0
    fams = json.loads(p.read_text(encoding="utf-8")).get("families", {})
    n = 0
    for it in bank.items.values():
        f = fams.get(it.template)
        if not f or not f.get("ok") or it.status not in (Status.REVISADO, Status.PILOTO, Status.CALIBRADO, Status.OPERATIVO):
            continue
        it.irt = IRTParams(f["a"], f["b"], 0.0)
        if it.status == Status.REVISADO:
            bank.promote(it.id, Status.PILOTO)
        if it.status == Status.PILOTO:
            bank.promote(it.id, Status.CALIBRADO)
        n += 1
    return n

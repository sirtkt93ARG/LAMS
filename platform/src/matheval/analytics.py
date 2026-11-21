"""Análisis clásico de ítems y plantillas (dificultad, discriminación, distractores, tiempos)."""
from __future__ import annotations
from collections import Counter, defaultdict
import numpy as np


def family_stats(rows: list[dict], items_by_id: dict) -> list[dict]:
    """rows: dicts con pid, item_id, score, response, duration_s. Una fila por plantilla."""
    by_pid = defaultdict(list)
    for r in rows:
        if r["score"] is not None:
            by_pid[r["pid"]].append(r)
    fam = defaultdict(lambda: {"n": 0, "correct": 0, "times": [], "tags": Counter(), "x": [], "rest": []})
    for pid, rs in by_pid.items():
        tot, n = sum(r["score"] for r in rs), len(rs)
        for r in rs:
            f = fam[r["item_id"].split("-")[0]]
            f["n"] += 1
            f["correct"] += int(r["score"] >= 0.5)
            if r.get("duration_s") is not None:
                f["times"].append(r["duration_s"])
            it = items_by_id.get(r["item_id"])
            if it is not None and r["score"] < 0.5 and it.kind == "choice":
                opt = next((o for o in it.options if o.id == r["response"]), None)
                if opt and opt.tag:
                    f["tags"][opt.tag] += 1
            if n >= 6:                                     # puntaje del resto de las respuestas de la persona
                f["x"].append(r["score"]); f["rest"].append((tot - r["score"]) / (n - 1))
    out = []
    for tid, f in sorted(fam.items()):
        p = f["correct"] / f["n"] if f["n"] else None
        disc = None
        if len(f["x"]) >= 30 and np.std(f["x"]) > 0 and np.std(f["rest"]) > 0:
            disc = float(np.corrcoef(f["x"], f["rest"])[0, 1])
        flags = []
        if f["n"] < 30: flags.append("pocos datos")
        else:
            if p < 0.15: flags.append("muy difícil")
            if p > 0.95: flags.append("muy fácil")
            if disc is not None and disc < 0.10: flags.append("discrimina poco")
        out.append({"template": tid, "n": f["n"], "p": None if p is None else round(p, 3),
                    "discrimination": None if disc is None else round(disc, 3),
                    "mean_time_s": round(float(np.mean(f["times"])), 1) if f["times"] else None,
                    "top_errors": dict(f["tags"].most_common(3)), "flags": flags})
    return out

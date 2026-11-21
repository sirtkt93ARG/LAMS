"""Diseño multietapa (3 etapas) y CAT con balance de contenido y control de exposición."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from collections import defaultdict
from .models import IRTParams
from .irt import eap, info


@dataclass
class PoolItem:
    id: str
    axis: str
    params: IRTParams
    fp: str | None = None     # huella del contenido: dos ítems con la misma huella son el mismo ejercicio


# ---- Multietapa -----------------------------------------------------------------------
@dataclass
class MSTDesign:
    stage1: list[str]
    stage2: dict[str, list[str]]   # claves: low | mid | high
    stage3: dict[str, list[str]]
    cut2: tuple[float, float] = (-1.6, -0.4)   # umbrales de ruteo tras la etapa 1
    cut3: tuple[float, float] = (-1.6, -0.2)   # umbrales de ruteo tras la etapa 2


def _round_robin(cands: list[PoolItem], center: float, size: int, rng: random.Random | None = None, spread: int = 1,
                 used_fp: set | None = None) -> list[PoolItem]:
    """Arma un bloque balanceado por eje con ítems cercanos a `center`. Con `rng`, cada elección se sortea entre los `spread`
    ítems más cercanos de su eje (control de exposición); nunca repite contenido (huella) dentro del diseño."""
    used_fp = used_fp if used_fp is not None else set()
    by_axis = defaultdict(list)
    for it in sorted(cands, key=lambda x: abs(x.params.b - center)):
        by_axis[it.axis].append(it)
    out, axes = [], sorted(by_axis)
    while len(out) < size and any(by_axis.values()):
        for ax in axes:
            lst = by_axis[ax]
            while lst and len(out) < size:
                it = lst.pop(rng.randrange(min(spread, len(lst))) if rng else 0)
                if it.fp is not None and it.fp in used_fp:
                    continue
                if it.fp is not None:
                    used_fp.add(it.fp)
                out.append(it)
                break
    return out


def build_design(pool: list[PoolItem], size: int = 8, center1: float = -1.0,
                 centers2=(-2.0, -1.0, 0.4), centers3=(-2.4, -0.9, 1.0),
                 rng: random.Random | None = None, spread: int = 16) -> MSTDesign:
    left, used_fp = list(pool), set()

    def take(center):
        blk = _round_robin(left, center, size, rng, spread, used_fp)
        ids = {it.id for it in blk}
        left[:] = [x for x in left if x.id not in ids and not (x.fp is not None and x.fp in used_fp)]
        return [it.id for it in blk]

    s1 = take(center1)
    s2 = {k: take(c) for k, c in zip(("low", "mid", "high"), centers2)}
    s3 = {k: take(c) for k, c in zip(("low", "mid", "high"), centers3)}
    return MSTDesign(s1, s2, s3)


def _route(theta: float, cuts) -> str:
    return "low" if theta < cuts[0] else ("high" if theta >= cuts[1] else "mid")


def design_to_dict(d: MSTDesign) -> dict:
    return {"stage1": d.stage1, "stage2": d.stage2, "stage3": d.stage3, "cut2": list(d.cut2), "cut3": list(d.cut3)}


def design_from_dict(x: dict) -> MSTDesign:
    return MSTDesign(x["stage1"], x["stage2"], x["stage3"], tuple(x["cut2"]), tuple(x["cut3"]))



class MSTSession:
    def __init__(self, design: MSTDesign, params: dict[str, IRTParams], prior_mean=0.0, prior_sd=1.5):
        self.d, self.params = design, params
        self.prior = (prior_mean, prior_sd)
        self.stage, self.route = 1, []
        self.answers: list[tuple[IRTParams, int]] = []
        self.administered: list[str] = []
        self.responses: list[list] = []          # [item_id, 0/1] en orden, para persistir y reconstruir
        self._pending = list(design.stage1)

    def snapshot(self) -> dict:
        """Estado serializable (JSON). Solo guarda los parámetros de los ítems del diseño."""
        d = self.d
        ids = set(d.stage1) | {i for b in d.stage2.values() for i in b} | {i for b in d.stage3.values() for i in b}
        return {"design": design_to_dict(d), "prior": list(self.prior), "responses": self.responses,
                "params": {i: [p.a, p.b, p.c] for i, p in self.params.items() if i in ids}}

    @classmethod
    def from_snapshot(cls, snap: dict) -> "MSTSession":
        params = {i: IRTParams(*v) for i, v in snap["params"].items()}
        s = cls(design_from_dict(snap["design"]), params, *snap["prior"])
        for item_id, ok in snap["responses"]:
            s.record(item_id, ok)
        return s

    def next_items(self) -> list[str]:
        return list(self._pending)

    def record(self, item_id: str, correct: int) -> None:
        self._pending.remove(item_id)
        self.administered.append(item_id)
        self.responses.append([item_id, int(correct)])
        self.answers.append((self.params[item_id], int(correct)))
        if not self._pending and self.stage < 3:
            theta, _ = self.estimate()
            key = _route(theta, self.d.cut2 if self.stage == 1 else self.d.cut3)
            self.route.append(key)
            self.stage += 1
            self._pending = list((self.d.stage2 if self.stage == 2 else self.d.stage3)[key])
        elif not self._pending:
            self.stage = 4  # finalizada

    @property
    def done(self) -> bool:
        return self.stage == 4

    def estimate(self):
        return eap(self.answers, *self.prior)


# ---- CAT ------------------------------------------------------------------------------
class CATSession:
    def __init__(self, pool: list[PoolItem], max_items=24, se_stop=0.0, top_k=3, seed=0,
                 prior_mean=0.0, prior_sd=1.5):
        self.pool = {p.id: p for p in pool}
        self.rng = random.Random(seed)
        self.max_items, self.se_stop, self.top_k = max_items, se_stop, top_k
        self.prior = (prior_mean, prior_sd)
        self.answers, self.administered = [], []
        self.axis_count = defaultdict(int)
        self.axes = sorted({p.axis for p in pool})

    def estimate(self):
        return eap(self.answers, *self.prior)

    @property
    def done(self) -> bool:
        if len(self.administered) >= self.max_items:
            return True
        return self.se_stop > 0 and len(self.administered) >= 6 and self.estimate()[1] <= self.se_stop

    def next_item(self) -> str | None:
        if self.done:
            return None
        theta, _ = self.estimate()
        n = len(self.administered)
        # balance de contenido: eje con mayor déficit respecto de una distribución pareja
        axis = min(self.axes, key=lambda a: (self.axis_count[a] - n / len(self.axes), self.rng.random()))
        cands = [p for i, p in self.pool.items() if i not in self.administered and p.axis == axis] \
            or [p for i, p in self.pool.items() if i not in self.administered]
        if not cands:
            return None
        cands.sort(key=lambda p: -float(info(theta, p.params.a, p.params.b, p.params.c)))
        return self.rng.choice(cands[: self.top_k]).id   # control de exposición "randomesque"

    def record(self, item_id: str, correct: int) -> None:
        p = self.pool[item_id]
        self.administered.append(item_id)
        self.axis_count[p.axis] += 1
        self.answers.append((p.params, int(correct)))

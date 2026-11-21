"""Sesiones alternativas con la misma interfaz que MSTSession: práctica dirigida por habilidad (escalera de
dificultad con ejercicios espejo) y forma fija de piloto para recoger datos de calibración."""
from __future__ import annotations
import random
from collections import defaultdict
from .irt import eap
from .levels import prior_difficulty
from .models import IRTParams, Item
from .skills import skills_of_item


def build_catalog(items: list[Item], skill: str) -> dict:
    cat = {"levels": defaultdict(list), "by_template": defaultdict(list), "level_of": {}, "kind": {}, "fp": {}}
    for it in items:
        if skill in skills_of_item(it.id):
            cat["levels"][it.target_level].append(it.id)
            cat["by_template"][it.template].append(it.id)
            cat["level_of"][it.id], cat["kind"][it.id] = it.target_level, it.kind
            cat["fp"][it.id] = it.provenance.get("fp", it.id)
    cat["levels"], cat["by_template"] = dict(cat["levels"]), dict(cat["by_template"])
    return cat


def _tid(item_id: str) -> str:
    return item_id.split("-")[0]


class DirectedSession:
    kind = "dirigida"

    def __init__(self, skill: str, catalog: dict, level: int, total: int = 10, seed: int = 0):
        if not catalog["levels"]:
            raise ValueError("no hay ejercicios aprobados para esta habilidad")
        self.skill, self.cat, self.level, self.total, self.seed = skill, catalog, level, total, seed
        self.levels = sorted(catalog["levels"])
        self.responses: list[list] = []           # [item_id, ok, nivel]
        self.administered: list[str] = []
        self.consec_wrong = 0
        self.pending = self._choose()

    def _nearest(self, lvl: int) -> int:
        return min(self.levels, key=lambda x: (abs(x - lvl), x))

    def _choose(self) -> str | None:
        if len(self.administered) >= self.total:
            return None
        rng = random.Random(f"{self.seed}:{len(self.administered)}")
        fp = self.cat.get("fp", {})
        asked_fp = {fp.get(i, i) for i in self.administered}
        asked = set(self.administered)
        if self.responses and not self.responses[-1][1] and self.consec_wrong == 1:      # ejercicio espejo
            cands = [i for i in self.cat["by_template"].get(_tid(self.responses[-1][0]), []) if i not in asked and fp.get(i, i) not in asked_fp]
            if cands:
                return rng.choice(cands)
        order = sorted(self.levels, key=lambda x: (abs(x - self.level), x))
        for lvl in order:
            cands = [i for i in self.cat["levels"][lvl] if i not in asked and fp.get(i, i) not in asked_fp]
            if self.responses:
                alt = [i for i in cands if _tid(i) != _tid(self.responses[-1][0])]
                cands = alt or cands
            if cands:
                return rng.choice(cands)
        return None

    def next_items(self) -> list[str]:
        return [self.pending] if self.pending else []

    @property
    def done(self) -> bool:
        return self.pending is None

    def record(self, item_id: str, correct: int) -> None:
        if item_id != self.pending:
            raise ValueError("ítem no pendiente")
        lvl = self.cat["level_of"][item_id]
        self.responses.append([item_id, int(correct), lvl, self.cat["kind"][item_id]])
        self.administered.append(item_id)
        idx = self.levels.index(self._nearest(self.level))
        if correct:
            self.consec_wrong = 0
            self.level = self.levels[min(idx + 1, len(self.levels) - 1)]
        else:
            self.consec_wrong += 1
            if self.consec_wrong >= 2:
                self.level, self.consec_wrong = self.levels[max(idx - 1, 0)], 0
        self.pending = self._choose()

    def estimate(self):
        resp = [(IRTParams(1.0, prior_difficulty(r[2]), 0.25 if r[3] == "choice" else 0.0), r[1]) for r in self.responses]
        return eap(resp, 0.0, 1.5)

    def snapshot(self) -> dict:
        return {"kind": self.kind, "skill": self.skill, "level": self.level, "total": self.total, "seed": self.seed,
                "responses": self.responses, "consec_wrong": self.consec_wrong, "start_level": getattr(self, "_start", self.level),
                "pending": self.pending}

    @classmethod
    def from_snapshot(cls, snap: dict, catalog: dict) -> "DirectedSession":
        s = cls.__new__(cls)
        s.skill, s.cat, s.level, s.total, s.seed = snap["skill"], catalog, snap["level"], snap["total"], snap["seed"]
        s.levels = sorted(catalog["levels"])
        s.responses = [list(r) for r in snap["responses"]]
        s.administered = [r[0] for r in s.responses]
        s.consec_wrong, s._start = snap["consec_wrong"], snap["start_level"]
        pend = snap.get("pending")
        s.pending = pend if (pend is None or pend in catalog["level_of"]) else s._choose()
        return s


def start_directed(skill: str, catalog: dict, level: int, total: int = 10, seed: int = 0) -> DirectedSession:
    s = DirectedSession(skill, catalog, level, total, seed)
    s._start = s.level
    return s


class FormSession:
    """Forma fija (una instancia por plantilla, en orden aleatorio) para recoger datos de calibración."""
    kind = "piloto"

    def __init__(self, item_ids: list[str], params: dict[str, list[float]], responses=None):
        self.ids, self.params = list(item_ids), params
        self.responses: list[list] = []
        self.administered: list[str] = []
        for i, ok in (responses or []):
            self.record(i, ok)

    def next_items(self) -> list[str]:
        return [self.ids[len(self.administered)]] if not self.done else []

    @property
    def done(self) -> bool:
        return len(self.administered) >= len(self.ids)

    def record(self, item_id: str, correct: int) -> None:
        if self.done or item_id != self.ids[len(self.administered)]:
            raise ValueError("ítem no pendiente")
        self.responses.append([item_id, int(correct)])
        self.administered.append(item_id)

    def estimate(self):
        return eap([(IRTParams(*self.params[i]), ok) for i, ok in self.responses], 0.0, 1.5)

    def snapshot(self) -> dict:
        return {"kind": self.kind, "ids": self.ids, "params": self.params, "responses": self.responses}

    @classmethod
    def from_snapshot(cls, snap: dict) -> "FormSession":
        return cls(snap["ids"], snap["params"], snap["responses"])


def build_form(items: list[Item], seed: int = 0) -> tuple[list[str], dict]:
    rng = random.Random(seed)
    by_t: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        by_t[it.template].append(it)
    chosen = [rng.choice(v) for _, v in sorted(by_t.items())]
    rng.shuffle(chosen)
    return [c.id for c in chosen], {c.id: [1.0, prior_difficulty(c.target_level), 0.25 if c.kind == "choice" else 0.0] for c in chosen}

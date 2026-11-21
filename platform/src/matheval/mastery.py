"""Dominio por habilidad (seguimiento bayesiano de conocimiento), repaso espaciado y recomendaciones."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from . import templates as T
from .skills import SKILLS, skills_of_item

P_INIT, P_TRANSIT = 0.20, 0.12
SLIP, GUESS_CHOICE, GUESS_OPEN = 0.10, 0.25, 0.05
INTERVALS = [(0.0, 1), (0.4, 2), (0.6, 4), (0.75, 7), (0.9, 14)]   # (p mínima, días hasta el próximo repaso)


@dataclass
class SkillState:
    p: float = P_INIT
    n: int = 0
    last: datetime | None = None


@lru_cache(maxsize=None)
def _guess(template: str) -> float:
    return GUESS_CHOICE if T.generate(template, 0).kind == "choice" else GUESS_OPEN


def bkt_update(p: float, correct: bool, guess: float, slip: float = SLIP, transit: float = P_TRANSIT) -> float:
    post = (p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)) if correct else (p * slip / (p * slip + (1 - p) * (1 - guess)))
    return post + (1 - post) * transit


def compute_mastery(rows) -> dict[str, SkillState]:
    """rows: iterable de (item_id, score, timestamp datetime|None, hints) en orden cronológico."""
    states: dict[str, SkillState] = {}
    for item_id, score, ts, hints in rows:
        if score is None:
            continue
        for sk in skills_of_item(item_id):
            st = states.setdefault(sk, SkillState())
            st.n += 1
            st.last = ts or st.last
            if hints:                                   # con ayuda no cuenta como evidencia de dominio
                continue
            st.p = bkt_update(st.p, score >= 0.5, _guess(item_id.split("-")[0]))
    return states


def due_days(p: float) -> int:
    return [d for th, d in INTERVALS if p >= th][-1]


def recommend(states: dict[str, SkillState], now: datetime | None = None, max_n: int = 3) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    out = []
    for sk, (name, prereqs) in SKILLS.items():
        st = states.get(sk)
        if st is None or st.n == 0:
            if all((states.get(q) is None or states[q].p >= 0.5) for q in prereqs):
                out.append((0.5, {"skill": sk, "name": name, "reason": "nuevo"}))
            continue
        if st.p < 0.6:
            out.append((1.0 - st.p, {"skill": sk, "name": name, "reason": "para reforzar"}))
        elif st.last and now - st.last >= timedelta(days=due_days(st.p)):
            out.append((0.3, {"skill": sk, "name": name, "reason": "repaso"}))
    out.sort(key=lambda x: -x[0])
    return [d for _, d in out[:max_n]]


def summary(states: dict[str, SkillState]) -> list[dict]:
    return [{"skill": sk, "name": name, "p_known": round(states[sk].p, 2) if sk in states else None,
             "n": states[sk].n if sk in states else 0} for sk, (name, _) in SKILLS.items()]

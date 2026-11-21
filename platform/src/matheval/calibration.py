"""Calibración 2PL por máxima verosimilitud marginal (EM) con datos faltantes.
Herramienta para el piloto: estima a y b de cada ítem a partir de una matriz estudiantes x ítems."""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize
from .irt import p_correct

Q = np.linspace(-4, 4, 41)
W0 = np.exp(-0.5 * Q ** 2)
W0 /= W0.sum()  # prior N(0,1) fija: define la escala


def calibrate_2pl(Y: np.ndarray, iters: int = 40, tol: float = 1e-4):
    """Y: matriz (N, J) con 1/0 y np.nan para ítems no presentados. Devuelve (a, b)."""
    N, J = Y.shape
    obs = ~np.isnan(Y)
    Yz = np.nan_to_num(Y)
    a, b = np.ones(J), np.zeros(J)
    for _ in range(iters):
        P = p_correct(Q[None, :], a[:, None], b[:, None])           # (J, Q)
        P = np.clip(P, 1e-6, 1 - 1e-6)
        ll = (obs * Yz) @ np.log(P) + (obs * (1 - Yz)) @ np.log(1 - P)   # (N, Q)
        post = np.exp(ll - ll.max(axis=1, keepdims=True)) * W0
        post /= post.sum(axis=1, keepdims=True)
        n_jq = obs.T.astype(float) @ post                                # (J, Q) personas esperadas
        r_jq = (obs * Yz).T @ post                                       # (J, Q) aciertos esperados
        new_a, new_b = a.copy(), b.copy()
        for j in range(J):
            def nll(x, j=j):
                p = np.clip(p_correct(Q, x[0], x[1]), 1e-6, 1 - 1e-6)
                return -(r_jq[j] * np.log(p) + (n_jq[j] - r_jq[j]) * np.log(1 - p)).sum()
            res = minimize(nll, [a[j], b[j]], bounds=[(0.3, 3.0), (-4.0, 4.0)], method="L-BFGS-B")
            new_a[j], new_b[j] = res.x
        delta = max(np.abs(new_a - a).max(), np.abs(new_b - b).max())
        a, b = new_a, new_b
        if delta < tol:
            break
    return a, b


def calibrate_2pl_long(person: np.ndarray, item: np.ndarray, y: np.ndarray, n_persons: int, n_items: int,
                       iters: int = 40, tol: float = 1e-4):
    """Calibración 2PL con datos en formato largo (una fila por respuesta). Permite varias respuestas de una
    persona al mismo ítem o familia de ítems. Devuelve (a, b)."""
    a, b = np.ones(n_items), np.zeros(n_items)
    person, item, y = np.asarray(person), np.asarray(item), np.asarray(y, dtype=float)
    for _ in range(iters):
        P = np.clip(p_correct(Q[None, :], a[:, None], b[:, None]), 1e-6, 1 - 1e-6)     # (J, Q)
        ll = np.zeros((n_persons, len(Q)))
        np.add.at(ll, person, y[:, None] * np.log(P[item]) + (1 - y[:, None]) * np.log(1 - P[item]))
        post = np.exp(ll - ll.max(axis=1, keepdims=True)) * W0
        post /= post.sum(axis=1, keepdims=True)
        n_jq, r_jq = np.zeros((n_items, len(Q))), np.zeros((n_items, len(Q)))
        np.add.at(n_jq, item, post[person])
        np.add.at(r_jq, item, post[person] * y[:, None])
        new_a, new_b = a.copy(), b.copy()
        for j in range(n_items):
            if n_jq[j].sum() == 0:
                continue
            def nll(x, j=j):
                pj = np.clip(p_correct(Q, x[0], x[1]), 1e-6, 1 - 1e-6)
                return -(r_jq[j] * np.log(pj) + (n_jq[j] - r_jq[j]) * np.log(1 - pj)).sum()
            res = minimize(nll, [a[j], b[j]], bounds=[(0.3, 3.0), (-4.0, 4.0)], method="L-BFGS-B")
            new_a[j], new_b[j] = res.x
        delta = max(np.abs(new_a - a).max(), np.abs(new_b - b).max())
        a, b = new_a, new_b
        if delta < tol:
            break
    return a, b


def calibrate_families(rows: list[tuple[str, str, float]], min_obs: int = 300) -> dict:
    """rows: (persona, id de ítem, puntaje 0/1). Estima un a y un b por plantilla (familia de ítems clonados).
    Devuelve {plantilla: {a, b, n_obs, ok}}; ok=True si hay al menos min_obs respuestas."""
    persons, fams = {}, {}
    pi, fi, yy = [], [], []
    for pid, item_id, score in rows:
        if score is None:
            continue
        pi.append(persons.setdefault(pid, len(persons)))
        fi.append(fams.setdefault(item_id.split("-")[0], len(fams)))
        yy.append(1.0 if score >= 0.5 else 0.0)
    if not yy:
        return {}
    a, b = calibrate_2pl_long(np.array(pi), np.array(fi), np.array(yy), len(persons), len(fams))
    counts = np.bincount(np.array(fi), minlength=len(fams))
    return {t: {"a": round(float(a[j]), 3), "b": round(float(b[j]), 3), "n_obs": int(counts[j]), "ok": bool(counts[j] >= min_obs)}
            for t, j in fams.items()}

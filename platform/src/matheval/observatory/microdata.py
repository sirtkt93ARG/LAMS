"""Estadística de PISA sobre microdatos: medias, proporciones, brechas y pendientes con errores estándar que combinan
la replicación balanceada repetida (BRR con ajuste de Fay) y la variabilidad entre valores plausibles (reglas de Rubin).

Sin dependencias de DuckDB ni pandas: recibe arreglos de NumPy. La lectura de archivos está en scripts/pisa_ingest.py.
Limitación: no incluye el error de vinculación (link error) que la OCDE agrega al comparar ciclos; para tendencias hay que
sumar el publicado por la OCDE (ver `trend_test`)."""
from __future__ import annotations
import numpy as np

FAY = 0.5
# Límites inferiores de los niveles de matemática de PISA 2022 (niveles 1c, 1b, 1a, 2, 3, 4, 5 y 6)
MATH_CUTS_2022 = (233.0, 295.0, 358.0, 420.0, 482.0, 545.0, 607.0, 669.0)
MATH_LEVEL_NAMES = ("bajo 1c", "1c", "1b", "1a", "2", "3", "4", "5", "6")


def _combine(theta: np.ndarray, theta_rep: np.ndarray, fay: float = FAY) -> tuple[float, float, dict]:
    """theta: (M,) estimación por valor plausible; theta_rep: (M, G) estimaciones con cada peso de replicación."""
    M, G = theta_rep.shape
    est = float(theta.mean())
    sampling = float(np.mean(((theta_rep - theta[:, None]) ** 2).sum(axis=1) / (G * (1 - fay) ** 2)))
    imputation = float(theta.var(ddof=1)) if M > 1 else 0.0
    total = sampling + (1 + 1 / M) * imputation
    return est, float(np.sqrt(total)), {"sampling_var": sampling, "imputation_var": imputation, "M": M, "G": G}


def _wmean(values: np.ndarray, w: np.ndarray, w_reps: np.ndarray):
    """values: (n, M). Devuelve (M,) y (M, G) de medias ponderadas."""
    full = (values * w[:, None]).sum(0) / w.sum()
    reps = (values.T @ w_reps) / w_reps.sum(0)[None, :]
    return full, reps


def _sel(mask, *arrs):
    return tuple(a if mask is None else a[mask] for a in arrs)


def mean_estimate(values: np.ndarray, w: np.ndarray, w_reps: np.ndarray, mask=None, fay: float = FAY) -> dict:
    v, ww, wr = _sel(mask, values, w, w_reps)
    full, reps = _wmean(v, ww, wr)
    est, se, d = _combine(full, reps, fay)
    return {"estimate": est, "se": se, "n": int(len(v)), **d}


def share_estimate(values: np.ndarray, w: np.ndarray, w_reps: np.ndarray, predicate, mask=None, fay: float = FAY) -> dict:
    """Proporción ponderada (en %) de estudiantes que cumplen `predicate(values) -> bool array`."""
    v, ww, wr = _sel(mask, values, w, w_reps)
    out = mean_estimate(predicate(v).astype(float), ww, wr, None, fay)
    return {**out, "estimate": 100 * out["estimate"], "se": 100 * out["se"]}


def gap_estimate(values: np.ndarray, w: np.ndarray, w_reps: np.ndarray, mask_a, mask_b, fay: float = FAY) -> dict:
    """Diferencia de medias A - B con error estándar (las dos medias se calculan sobre los mismos pesos de replicación)."""
    fa, ra = _wmean(*_sel(mask_a, values, w)[:1], *_sel(mask_a, w, w_reps))
    fb, rb = _wmean(*_sel(mask_b, values, w)[:1], *_sel(mask_b, w, w_reps))
    est, se, d = _combine(fa - fb, ra - rb, fay)
    return {"estimate": est, "se": se, **d}


def level_shares(values: np.ndarray, w: np.ndarray, w_reps: np.ndarray, cuts=MATH_CUTS_2022, mask=None, fay: float = FAY) -> list[dict]:
    """Porcentaje de estudiantes en cada nivel (de «bajo el primero» al último) con sus errores estándar."""
    edges = (-np.inf, *cuts, np.inf)
    out = []
    for k in range(len(edges) - 1):
        r = share_estimate(values, w, w_reps, lambda x, a=edges[k], b=edges[k + 1]: (x >= a) & (x < b), mask, fay)
        out.append({"level": MATH_LEVEL_NAMES[k] if len(cuts) == 8 else str(k), "share": r["estimate"], "se": r["se"]})
    return out


def weighted_quantiles(x: np.ndarray, w: np.ndarray, qs=(0.25, 0.5, 0.75)) -> list[float]:
    o = np.argsort(x)
    xs, cw = x[o], np.cumsum(w[o])
    cw = (cw - 0.5 * w[o]) / cw[-1]
    return [float(np.interp(q, cw, xs)) for q in qs]


def quartile_masks(x: np.ndarray, w: np.ndarray) -> list[np.ndarray]:
    """Máscaras de los cuartiles ponderados de un índice (por ejemplo ESCS): Q1 (más bajo) a Q4 (más alto)."""
    q1, q2, q3 = weighted_quantiles(x, w)
    return [x <= q1, (x > q1) & (x <= q2), (x > q2) & (x <= q3), x > q3]


def slope_estimate(values: np.ndarray, x: np.ndarray, w: np.ndarray, w_reps: np.ndarray, fay: float = FAY) -> dict:
    """Pendiente de la regresión ponderada del puntaje sobre un índice (gradiente socioeconómico)."""
    def slope(wt):
        xm = (x * wt).sum() / wt.sum()
        vm = (values * wt[:, None]).sum(0) / wt.sum()
        return (wt[:, None] * (x - xm)[:, None] * (values - vm)).sum(0) / (wt * (x - xm) ** 2).sum()
    full = slope(w)
    reps = np.stack([slope(w_reps[:, g]) for g in range(w_reps.shape[1])], axis=1)
    est, se, d = _combine(full, reps, fay)
    return {"estimate": est, "se": se, **d}


def significant_difference(est_a: float, se_a: float, est_b: float, se_b: float, link_error: float = 0.0, z: float = 1.96) -> dict:
    """Prueba de la diferencia B - A entre dos ciclos. `link_error` es el error de vinculación publicado por la OCDE."""
    d = est_b - est_a
    se = float(np.sqrt(se_a ** 2 + se_b ** 2 + link_error ** 2))
    return {"diff": d, "se": se, "z": d / se if se else float("nan"), "significant": bool(se and abs(d / se) > z)}

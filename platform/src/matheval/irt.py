"""Teoría de respuesta al ítem: modelo logístico de 3 parámetros y estimación EAP."""
from __future__ import annotations
import numpy as np
from .models import IRTParams

GRID = np.linspace(-4.5, 4.5, 91)


def p_correct(theta, a, b, c=0.0):
    return c + (1.0 - c) / (1.0 + np.exp(-a * (np.asarray(theta, dtype=float) - b)))


def info(theta, a, b, c=0.0):
    p = p_correct(theta, a, b, c)
    q = 1.0 - p
    return (a ** 2) * ((p - c) / (1.0 - c)) ** 2 * q / np.maximum(p, 1e-12)


def eap(responses: list[tuple[IRTParams, int]], prior_mean: float = 0.0, prior_sd: float = 1.5):
    """Devuelve (theta, error estándar). responses: lista de (parámetros, 0/1)."""
    logpost = -0.5 * ((GRID - prior_mean) / prior_sd) ** 2
    for prm, y in responses:
        p = np.clip(p_correct(GRID, prm.a, prm.b, prm.c), 1e-9, 1 - 1e-9)
        logpost = logpost + (np.log(p) if y else np.log(1 - p))
    w = np.exp(logpost - logpost.max())
    w /= w.sum()
    theta = float((w * GRID).sum())
    se = float(np.sqrt((w * (GRID - theta) ** 2).sum()))
    return theta, se

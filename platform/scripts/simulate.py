"""Simulación: ¿mejora la medición con diseño adaptativo en una cohorte con desempeño mayormente bajo?
Datos SIMULADOS: sirven para validar el diseño del motor, no para afirmar nada sobre estudiantes reales."""
import sys, random
import numpy as np
sys.path.insert(0, "src")
from matheval.models import IRTParams
from matheval.irt import p_correct, eap
from matheval.levels import level_of
from matheval.adaptive import PoolItem, build_design, MSTSession, CATSession

R = np.random.default_rng(2026)
axes = ["numeros_algebra", "funciones_relaciones", "geometria_medida", "datos_azar"]
pool = [PoolItem(f"i{k}", axes[k % 4], IRTParams(float(R.uniform(.8, 1.6)), float(np.clip(R.normal(-.5, 1.3), -3, 3)), 0.0))
        for k in range(400)]
params = {p.id: p.params for p in pool}
N, LEN = 3000, 24
theta = R.normal(-1.3, 1.0, N)          # cohorte simulada: ~73% por debajo de la hipótesis de nivel mínimo (theta < -0.7)
print(f"Cohorte simulada: {N} estudiantes, media {theta.mean():.2f}, por debajo de N4: {(theta < -0.7).mean():.0%}")


def answer(th, iid, rng):
    p = params[iid]
    return int(rng.random() < p_correct(th, p.a, p.b, p.c))


def fixed_form(center, spread):
    srt = sorted(pool, key=lambda p: abs(p.params.b - center))
    cand = srt[:80]
    by = {}
    for p in cand:
        by.setdefault(p.axis, []).append(p)
    out = []
    i = 0
    while len(out) < LEN:
        for ax in axes:
            if len(out) < LEN:
                out.append(by[ax][i])
        i += 1
    return [p.id for p in out]


def run_fixed(form, seed):
    rng = random.Random(seed)
    est = []
    for th in theta:
        resp = [(params[i], answer(th, i, rng)) for i in form]
        est.append(eap(resp)[0])
    return np.array(est)


def run_mst(seed):
    rng = random.Random(seed)
    d = build_design(pool, size=8, center1=-1.0)
    est = []
    for th in theta:
        s = MSTSession(d, params)
        while not s.done:
            for iid in s.next_items():
                s.record(iid, answer(th, iid, rng))
        est.append(s.estimate()[0])
    return np.array(est)


def run_cat(seed):
    rng = random.Random(seed)
    est = []
    for k, th in enumerate(theta):
        s = CATSession(pool, max_items=LEN, seed=seed + k)
        while (iid := s.next_item()) is not None:
            s.record(iid, answer(th, iid, rng))
        est.append(s.estimate()[0])
    return np.array(est)


designs = {
    "Forma fija centrada en 0 (como la media OCDE)": run_fixed(fixed_form(0.0, 1), 1),
    "Forma fija centrada en la cohorte (-1,3)": run_fixed(fixed_form(-1.3, 1), 2),
    "Multietapa 3 etapas (8+8+8)": run_mst(3),
    "CAT con balance de contenido": run_cat(4),
}
true_lv = np.array([level_of(t) for t in theta])
print(f"\n{'Diseño (24 ítems)':48s} {'RMSE':>6s} {'RMSE θ<-0,7':>12s} {'nivel exacto':>13s} {'±1 nivel':>9s} {'clasif. N4 ok':>14s}")
for name, est in designs.items():
    err = est - theta
    low = theta < -0.7
    lv = np.array([level_of(t) for t in est])
    base_true, base_est = theta >= -0.7, est >= -0.7
    print(f"{name:48s} {np.sqrt((err**2).mean()):6.3f} {np.sqrt((err[low]**2).mean()):12.3f} "
          f"{(lv == true_lv).mean():13.1%} {(abs(lv - true_lv) <= 1).mean():9.1%} {(base_true == base_est).mean():14.1%}")

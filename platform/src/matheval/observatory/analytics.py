from __future__ import annotations
import numpy as np
from .data import AVG_NAME, GapRow, Obs
from .microdata import significant_difference

POINTS_PER_YEAR = 20      # regla orientativa de la OCDE: unos 20 puntos de PISA equivalen a un año de escolaridad


def entities(rows: list[Obs], domain: str | None = None) -> list[dict]:
    seen: dict[str, str] = {}
    for o in rows:
        if o.mean is not None and (domain is None or o.domain == domain):
            seen.setdefault(o.entity, o.group)
    return [{"entity": e, "group": g} for e, g in seen.items()]


def series(rows: list[Obs], entity: str, domain: str) -> list[tuple[int, float]]:
    return sorted((o.cycle, o.mean) for o in rows if o.entity == entity and o.domain == domain and o.mean is not None)


def series_se(rows: list[Obs], entity: str, domain: str) -> list[tuple[int, float | None]]:
    return sorted((o.cycle, o.se) for o in rows if o.entity == entity and o.domain == domain and o.mean is not None)


def significant_changes(rows: list[Obs], entity: str, domain: str, link_errors: dict[tuple[int, int], float] | None = None) -> list[dict]:
    """Cambios entre ciclos consecutivos con prueba de significancia, solo si ambos extremos tienen error estándar.
    `link_errors` permite sumar el error de vinculación de la OCDE por par de ciclos."""
    pts = {o.cycle: (o.mean, o.se) for o in rows if o.entity == entity and o.domain == domain and o.mean is not None}
    cyc = sorted(pts)
    out = []
    for a, b in zip(cyc, cyc[1:]):
        (ma, sa), (mb, sb) = pts[a], pts[b]
        if sa is None or sb is None:
            continue
        t = significant_difference(ma, sa, mb, sb, (link_errors or {}).get((a, b), 0.0))
        out.append({"from": a, "to": b, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in t.items()}})
    return out


def gaps_for(gaps: list[GapRow], entity: str, domain: str) -> list[dict]:
    return [{"cycle": g.cycle, "dimension": g.dimension, "group": g.group, "value": round(g.value, 2),
             "se": None if g.se is None else round(g.se, 2), "n": g.n, "quality": g.quality}
            for g in gaps if g.entity == entity and g.domain == domain]


def trend_stats(s: list[tuple[int, float]]) -> dict | None:
    if len(s) < 2:
        return None
    xs, ys = np.array([c for c, _ in s], float), np.array([v for _, v in s], float)
    slope = float(np.polyfit(xs, ys, 1)[0])
    return {"first_cycle": s[0][0], "first": s[0][1], "last_cycle": s[-1][0], "last": s[-1][1],
            "total_change": s[-1][1] - s[0][1], "slope_per_year": round(slope, 2),
            "short_change": s[-1][1] - s[-2][1], "short_from": s[-2][0], "n_cycles": len(s),
            "gaps": [(a, b) for (a, _), (b, _) in zip(s, s[1:]) if b - a > 3]}


def compare(rows: list[Obs], domain: str, cycle: int, selected: list[str] | None = None) -> list[dict]:
    ref = next((o.mean for o in rows if o.entity == AVG_NAME and o.domain == domain and o.cycle == cycle and o.mean is not None), None)
    out = [{"entity": o.entity, "group": o.group, "mean": o.mean, "quality": o.quality,
            "gap_vs_oecd": None if ref is None else round(o.mean - ref, 1),
            "years_vs_oecd": None if ref is None else round((o.mean - ref) / POINTS_PER_YEAR, 1)}
           for o in rows if o.domain == domain and o.cycle == cycle and o.mean is not None
           and (selected is None or o.entity in selected)]
    return sorted(out, key=lambda r: -r["mean"])


def region_average(rows: list[Obs], domain: str, group: str = "America Latina", min_entities: int = 3) -> list[tuple[int, float]]:
    by: dict[int, list[float]] = {}
    for o in rows:
        if o.domain == domain and o.group == group and o.mean is not None:
            by.setdefault(o.cycle, []).append(o.mean)
    return sorted((c, round(sum(v) / len(v), 1)) for c, v in by.items() if len(v) >= min_entities)


def below_level2(rows: list[Obs], entity: str, domain: str = "matematica") -> list[dict]:
    return sorted(({"cycle": o.cycle, "value": o.below_l2, "quality": o.below_quality}
                   for o in rows if o.entity == entity and o.domain == domain and o.below_l2 is not None), key=lambda r: r["cycle"])


def focus(rows: list[Obs], entity: str) -> dict:
    """Resumen de una entidad: tendencia por dominio, brecha con el promedio OCDE y evolución del % bajo el nivel 2."""
    out = {"entity": entity, "domains": {}, "below_level2": below_level2(rows, entity)}
    for dom in ("matematica", "lectura", "ciencias"):
        s = series(rows, entity, dom)
        st = trend_stats(s)
        if not st:
            continue
        cmp_row = next((r for r in compare(rows, dom, st["last_cycle"], [entity])), None)
        out["domains"][dom] = {**st, "gap_vs_oecd": cmp_row and cmp_row["gap_vs_oecd"], "years_vs_oecd": cmp_row and cmp_row["years_vs_oecd"]}
    return out


def provenance(rows: list[Obs], domain: str, selected: list[str]) -> list[dict]:
    seen, out = set(), []
    for o in rows:
        if o.domain == domain and o.entity in selected and (o.source, o.url, o.quality) not in seen:
            seen.add((o.source, o.url, o.quality))
            out.append({"source": o.source, "url": o.url, "quality": o.quality})
    return out

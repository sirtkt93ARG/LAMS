from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path

DOMAINS = {"matematica": "Matemática", "lectura": "Lectura", "ciencias": "Ciencias"}
CYCLES = (2000, 2003, 2006, 2009, 2012, 2015, 2018, 2022, 2025)
QUALITIES = ("oficial_ocde", "secundaria", "microdatos_propios")
AVG_NAME = "OCDE (promedio de tendencia)"


@dataclass(frozen=True)
class Obs:
    cycle: int
    domain: str
    entity: str
    group: str
    mean: float | None
    below_l2: float | None
    top_l5_6: float | None
    source: str
    url: str
    quality: str
    note: str
    below_quality: str = ""
    se: float | None = None
    below_se: float | None = None


def _f(x: str) -> float | None:
    return float(x) if x not in ("", None) else None


def load_csv(path: str | Path) -> list[Obs]:
    with open(path, encoding="utf-8", newline="") as f:
        return [Obs(int(r["ciclo"]), r["dominio"], r["entidad"], r["grupo"], _f(r["media"]), _f(r["bajo_nivel2"]),
                    _f(r["niveles5y6"]), r["fuente"], r["url"], r["calidad"], r["nota"],
                    r.get("calidad_bajo_nivel2", ""), _f(r.get("error_estandar", "")), _f(r.get("bajo_nivel2_se", ""))) for r in csv.DictReader(f)]


def validate(rows: list[Obs]) -> list[str]:
    errs, seen = [], set()
    for o in rows:
        key = (o.cycle, o.domain, o.entity)
        where = f"{o.entity} {o.domain} {o.cycle}"
        if key in seen: errs.append(f"duplicado: {where}")
        seen.add(key)
        if o.cycle not in CYCLES: errs.append(f"ciclo inválido: {where}")
        if o.domain not in DOMAINS: errs.append(f"dominio inválido: {where}")
        if o.mean is not None and not 200 <= o.mean <= 700: errs.append(f"media fuera de rango: {where}")
        for name, v in (("bajo_nivel2", o.below_l2), ("niveles5y6", o.top_l5_6)):
            if v is not None and not 0 <= v <= 100: errs.append(f"{name} fuera de rango: {where}")
        if o.quality not in QUALITIES: errs.append(f"calidad inválida: {where}")
        if o.below_l2 is not None and o.below_quality not in QUALITIES: errs.append(f"calidad inválida del % bajo nivel 2: {where}")
        if not o.source or not o.url.startswith("http"): errs.append(f"falta fuente o enlace: {where}")
        if o.mean is None and o.below_l2 is None: errs.append(f"fila sin datos: {where}")
        for name, v in (("error_estandar", o.se), ("bajo_nivel2_se", o.below_se)):
            if v is not None and not 0 <= v <= 60: errs.append(f"{name} fuera de rango: {where}")
    return errs


@dataclass(frozen=True)
class GapRow:
    cycle: int
    domain: str
    entity: str
    dimension: str      # genero | genero_brecha | escs_cuartil | escs_brecha | escs_pendiente
    group: str
    value: float
    se: float | None
    n: int | None
    source: str
    quality: str


def load_gaps(path: str | Path) -> list[GapRow]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return [GapRow(int(r["ciclo"]), r["dominio"], r["entidad"], r["dimension"], r["grupo"], float(r["valor"]), _f(r["error_estandar"]),
                       int(float(r["n"])) if r["n"] else None, r["fuente"], r["calidad"]) for r in csv.DictReader(f)]

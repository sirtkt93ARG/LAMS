"""Calcula agregados de PISA con errores estándar a partir de los microdatos oficiales de la OCDE y los vuelca en el CSV del
observatorio. Los microdatos no se guardan ni se redistribuyen: solo se conservan los agregados."""
from __future__ import annotations
import csv
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from . import microdata as MD

DOMAIN_CODE = {"matematica": "MATH", "lectura": "READ", "ciencias": "SCIE"}
AGG_FIELDS = ["ciclo", "dominio", "entidad", "grupo", "media", "error_estandar", "bajo_nivel2", "bajo_nivel2_se", "niveles5y6",
              "fuente", "url", "calidad", "calidad_bajo_nivel2", "nota"]
GAP_FIELDS = ["ciclo", "dominio", "entidad", "dimension", "grupo", "valor", "error_estandar", "n", "fuente", "calidad"]
SOURCE = "Cálculo propio sobre los microdatos de PISA de la OCDE (replicación BRR y valores plausibles)"
DATA_URL = "https://www.oecd.org/pisa/data/"


@dataclass
class ColumnSpec:
    country: str = "CNT"
    weight: str = "W_FSTUWT"
    rep_prefix: str = "W_FSTURWT"
    n_reps: int = 80
    pv: str = "PV{m}{code}"           # PV1MATH ... PV10MATH
    n_pv: int = 10
    escs: str = "ESCS"
    gender: str = "ST004D01T"
    gender_codes: dict = field(default_factory=lambda: {1: "femenino", 2: "masculino"})

    def columns(self, domains) -> list[str]:
        cols = [self.country, self.weight, self.escs, self.gender] + [f"{self.rep_prefix}{g}" for g in range(1, self.n_reps + 1)]
        for d in domains:
            cols += [self.pv.format(m=m, code=DOMAIN_CODE[d]) for m in range(1, self.n_pv + 1)]
        return cols


def load_table(path: str | Path, columns: list[str], countries: list[str], country_col: str = "CNT") -> dict[str, np.ndarray]:
    """Lee solo las columnas y los países necesarios. Usa DuckDB si está instalado (csv/parquet); si no, pandas; .sav con pyreadstat."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".csv", ".parquet", ".txt"):
        try:
            import duckdb
            reader = "read_parquet" if suffix == ".parquet" else "read_csv_auto"
            cols = ", ".join(f'"{c}"' for c in columns)
            lst = ", ".join("'" + c.replace("'", "''") + "'" for c in countries)
            df = duckdb.connect().execute(f"SELECT {cols} FROM {reader}('{p.as_posix()}') WHERE \"{country_col}\" IN ({lst})").df()
        except ImportError:
            try:
                import pandas as pd
            except ImportError as e:
                raise RuntimeError("Instalá DuckDB o pandas: pip install -e \".[microdata]\"") from e
            df = pd.read_parquet(p, columns=columns) if suffix == ".parquet" else pd.read_csv(p, usecols=columns)
            df = df[df[country_col].isin(countries)]
    elif suffix == ".sav":
        try:
            import pyreadstat
        except ImportError as e:
            raise RuntimeError("Para leer archivos .sav instalá pyreadstat: pip install -e \".[microdata]\"") from e
        df, _ = pyreadstat.read_sav(str(p), usecols=columns)
        df = df[df[country_col].isin(countries)]
    else:
        raise ValueError(f"Formato no admitido: {suffix} (usar .csv, .parquet o .sav)")
    if len(df) == 0:
        raise ValueError(f"No hay filas para los países {countries} en el archivo")
    return {c: df[c].to_numpy() for c in df.columns}


def _arrays(t: dict[str, np.ndarray], spec: ColumnSpec, domain: str):
    ok = np.isfinite(t[spec.weight].astype(float)) & (t[spec.weight].astype(float) > 0)
    pvs = np.column_stack([t[spec.pv.format(m=m, code=DOMAIN_CODE[domain])].astype(float) for m in range(1, spec.n_pv + 1)])
    reps = np.column_stack([t[f"{spec.rep_prefix}{g}"].astype(float) for g in range(1, spec.n_reps + 1)])
    ok &= np.isfinite(pvs).all(axis=1) & np.isfinite(reps).all(axis=1)
    return pvs[ok], t[spec.weight].astype(float)[ok], reps[ok], ok


def compute(table: dict[str, np.ndarray], spec: ColumnSpec, domains: list[str], level2_cut: float = 420.07) -> dict:
    """Devuelve {'aggregates': {dominio: {...}}, 'gaps': [filas]} para un país (la tabla ya está filtrada)."""
    out: dict = {"aggregates": {}, "gaps": []}
    for d in domains:
        pvs, w, reps, ok = _arrays(table, spec, d)
        m = MD.mean_estimate(pvs, w, reps)
        agg = {"mean": m["estimate"], "se": m["se"], "n": m["n"]}
        if d == "matematica":
            b = MD.share_estimate(pvs, w, reps, lambda x: x < level2_cut)
            t = MD.share_estimate(pvs, w, reps, lambda x: x >= 607.0)
            agg.update({"below_l2": b["estimate"], "below_l2_se": b["se"], "top_5_6": t["estimate"]})
        out["aggregates"][d] = agg
        gcol = table[spec.gender][ok]
        masks = {name: gcol == code for code, name in spec.gender_codes.items()}
        names = list(masks)
        for name, mk in masks.items():
            r = MD.mean_estimate(pvs, w, reps, mk)
            out["gaps"].append({"dominio": d, "dimension": "genero", "grupo": name, "valor": r["estimate"], "error_estandar": r["se"], "n": r["n"]})
        if len(names) == 2:
            g = MD.gap_estimate(pvs, w, reps, masks[names[0]], masks[names[1]])
            out["gaps"].append({"dominio": d, "dimension": "genero_brecha", "grupo": f"{names[0]} menos {names[1]}", "valor": g["estimate"],
                                "error_estandar": g["se"], "n": int(sum(mk.sum() for mk in masks.values()))})
        escs = table[spec.escs].astype(float)[ok]
        valid = np.isfinite(escs)
        if valid.sum() > 100:
            qm = MD.quartile_masks(np.where(valid, escs, 0.0), w * valid)
            qm = [q & valid for q in qm]
            for k, mk in enumerate(qm, start=1):
                r = MD.mean_estimate(pvs, w, reps, mk)
                out["gaps"].append({"dominio": d, "dimension": "escs_cuartil", "grupo": f"Q{k}", "valor": r["estimate"], "error_estandar": r["se"], "n": r["n"]})
            g = MD.gap_estimate(pvs, w, reps, qm[3], qm[0])
            out["gaps"].append({"dominio": d, "dimension": "escs_brecha", "grupo": "Q4 menos Q1", "valor": g["estimate"], "error_estandar": g["se"], "n": int((qm[0] | qm[3]).sum())})
            s = MD.slope_estimate(pvs[valid], escs[valid], w[valid], reps[valid])
            out["gaps"].append({"dominio": d, "dimension": "escs_pendiente", "grupo": "puntos por unidad de ESCS", "valor": s["estimate"], "error_estandar": s["se"], "n": int(valid.sum())})
    return out


def _read(path: Path, fields: list[str]) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return [{k: r.get(k, "") for k in fields} for r in csv.DictReader(f)]


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def merge_into_csvs(result: dict, cycle: int, entity: str, group: str, agg_path: Path, gaps_path: Path, tolerance: float = 2.0) -> list[dict]:
    """Completa los errores estándar del CSV de agregados y agrega las brechas. Devuelve el informe de conciliación."""
    rows = _read(agg_path, AGG_FIELDS)
    report = []
    for d, a in result["aggregates"].items():
        row = next((r for r in rows if r["ciclo"] == str(cycle) and r["dominio"] == d and r["entidad"] == entity), None)
        published = float(row["media"]) if row and row["media"] != "" else None
        diff = None if published is None else round(a["mean"] - published, 1)
        report.append({"dominio": d, "calculada": round(a["mean"], 1), "se": round(a["se"], 2), "publicada": published, "diferencia": diff,
                       "conciliada": diff is not None and abs(diff) <= tolerance, "n": a["n"]})
        if row is None:
            row = dict.fromkeys(AGG_FIELDS, "")
            row.update(ciclo=cycle, dominio=d, entidad=entity, grupo=group, media=round(a["mean"], 1), fuente=SOURCE, url=DATA_URL,
                       calidad="microdatos_propios", nota="Calculado por el proyecto: contrastar con la tabla oficial de la OCDE")
            rows.append(row)
        row["error_estandar"] = round(a["se"], 2)
        if "below_l2" in a:
            row["bajo_nivel2"], row["bajo_nivel2_se"] = round(a["below_l2"], 1), round(a["below_l2_se"], 2)
            row["niveles5y6"] = round(a["top_5_6"], 1)
            row["calidad_bajo_nivel2"] = "microdatos_propios"
    gaps = _read(gaps_path, GAP_FIELDS)
    gaps = [g for g in gaps if not (g["ciclo"] == str(cycle) and g["entidad"] == entity)]
    for g in result["gaps"]:
        gaps.append({"ciclo": cycle, "entidad": entity, "fuente": SOURCE, "calidad": "microdatos_propios",
                     **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in g.items()}})
    rows.sort(key=lambda r: (r["dominio"], r["entidad"], int(r["ciclo"])))
    _write(agg_path, AGG_FIELDS, rows)
    _write(gaps_path, GAP_FIELDS, sorted(gaps, key=lambda g: (g["dominio"], g["entidad"], int(g["ciclo"]), g["dimension"], g["grupo"])))
    return report


def run(path, cycle: int, country_code: str, entity: str, group: str = "America Latina", domains=("matematica", "lectura", "ciencias"),
        spec: ColumnSpec | None = None, agg_path="data/observatory/pisa_agregados.csv", gaps_path="data/observatory/pisa_brechas.csv") -> list[dict]:
    spec = spec or ColumnSpec()
    table = load_table(path, spec.columns(domains), [country_code], spec.country)
    result = compute(table, spec, list(domains))
    return merge_into_csvs(result, cycle, entity, group, Path(agg_path), Path(gaps_path))

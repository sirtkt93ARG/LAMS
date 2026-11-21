"""Formato y lectura de números con convención rioplatense (punto de miles, coma decimal)."""
from __future__ import annotations
import re


def fmt_int(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def fmt_ars(n: int) -> str:
    return "$" + fmt_int(n)


def fmt_num(x: float, decimals: int = 1) -> str:
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def fmt_pct(x: float, decimals: int = 0) -> str:
    return fmt_num(x, decimals) + " %"


def parse_es_number(s) -> float | None:
    t = str(s).strip().replace("$", "").replace("%", "").replace(" ", "").replace("\u00a0", "")
    if not t or not re.fullmatch(r"[-+]?[\d.,]+", t):
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    elif "." in t and re.fullmatch(r"[-+]?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None

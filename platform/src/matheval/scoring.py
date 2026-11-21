from __future__ import annotations
from dataclasses import dataclass
from .models import Item
from .numfmt import parse_es_number
from .safe_expr import equivalent


@dataclass
class Result:
    score: float | None      # None = requiere corrección manual
    tag: str | None = None   # diagnóstico del error (si se conoce)
    normalized: str | None = None


def score_response(item: Item, response) -> Result:
    if response is None or str(response).strip() == "":
        return Result(0.0, "sin_respuesta", "")
    if item.kind == "choice":
        chosen = next((o for o in item.options if o.id == str(response).strip()), None)
        if chosen is None:
            return Result(0.0, "opcion_invalida", str(response))
        ok = chosen.id == item.correct
        return Result(1.0 if ok else 0.0, None if ok else chosen.tag, chosen.id)
    if item.kind == "numeric":
        x = parse_es_number(response)
        if x is None:
            return Result(0.0, "formato_invalido", str(response))
        ok = abs(x - float(item.correct)) <= item.tolerance + 1e-9
        return Result(1.0 if ok else 0.0, None if ok else "valor_incorrecto", str(x))
    if item.kind == "expression":
        ok = equivalent(str(response), str(item.correct), tuple(item.variables or ["n"]))
        return Result(1.0 if ok else 0.0, None if ok else "expresion_no_equivalente", str(response))
    if item.kind == "open":
        return Result(None, "correccion_manual", str(response))
    raise ValueError(f"tipo de ítem desconocido: {item.kind}")

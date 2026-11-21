"""Validación integral del banco generado y de sus exportaciones QTI 3.0.

Ejecutar desde platform: python scripts/validate_bank.py
"""
from __future__ import annotations

import collections
import pathlib
import sys

from lxml import etree

from matheval.bank import ItemBank
from matheval.qti3 import QTI_NS
from matheval.templates import SPEC

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "data" / "bank_demo.jsonl"
QTI_DIR = ROOT / "data" / "qti"
EXPECTED_QTI_PER_TEMPLATE = 20
MIN_ITEMS_PER_TEMPLATE = 50


def main() -> int:
    bank = ItemBank.load(str(BANK_PATH))
    counts = collections.Counter(item.template for item in bank.items.values())
    fingerprints = [item.provenance.get("fp") for item in bank.items.values()]
    missing = sum(not fp for fp in fingerprints)
    duplicates = len(fingerprints) - len(set(fp for fp in fingerprints if fp))
    if missing:
        raise SystemExit(f"ERROR: {missing} ítems no tienen huella de contenido")
    if duplicates:
        raise SystemExit(f"ERROR: {duplicates} huellas de contenido duplicadas")
    absent = sorted(set(SPEC) - set(counts))
    small = {tid: counts[tid] for tid in SPEC if counts[tid] < MIN_ITEMS_PER_TEMPLATE}
    if absent or small:
        raise SystemExit(f"ERROR: cobertura insuficiente; sin plantillas={absent}, por debajo del mínimo={small}")
    if set(counts) - set(SPEC):
        raise SystemExit(f"ERROR: plantillas desconocidas: {sorted(set(counts) - set(SPEC))}")

    qti_files = sorted(QTI_DIR.glob("*.xml"))
    expected = len(SPEC) * EXPECTED_QTI_PER_TEMPLATE
    if len(qti_files) != expected:
        raise SystemExit(f"ERROR: se esperaban {expected} XML QTI y hay {len(qti_files)}")
    seen_ids = set()
    for path in qti_files:
        try:
            root = etree.parse(str(path)).getroot()
        except (OSError, etree.XMLSyntaxError) as exc:
            raise SystemExit(f"ERROR: XML inválido {path.name}: {exc}") from exc
        item_id = root.get("identifier")
        if not item_id or item_id not in bank.items:
            raise SystemExit(f"ERROR: {path.name} no corresponde a un ítem del banco")
        if item_id in seen_ids:
            raise SystemExit(f"ERROR: identificador QTI duplicado: {item_id}")
        seen_ids.add(item_id)
        ns = {"q": QTI_NS}
        if not root.xpath("string(.//q:qti-correct-response/q:qti-value)", namespaces=ns):
            raise SystemExit(f"ERROR: falta respuesta correcta en {path.name}")

    print(f"OK: {len(bank.items)} ítems; {len(fingerprints)} huellas únicas; {len(SPEC)} plantillas; {len(qti_files)} XML QTI válidos.")
    print("Por plantilla: " + ", ".join(f"{tid}={counts[tid]}" for tid in sorted(counts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

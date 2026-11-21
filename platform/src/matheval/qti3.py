"""Exportación de ítems a QTI 3.0 (XML). El esquema XSD oficial no se validó aquí (sin red):
validar la salida con el validador de 1EdTech antes de importarla en otro sistema."""
from __future__ import annotations
from lxml import etree
from .models import Item

QTI_NS = "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def _q(tag: str) -> str:
    return f"{{{QTI_NS}}}{tag}"


def _sub(parent, tag, text=None, **attrs):
    el = etree.SubElement(parent, _q(tag), **attrs)
    if text is not None:
        el.text = text
    return el


def _score_block(rp, cond_children_factory):
    cond = _sub(rp, "qti-response-condition")
    r_if = _sub(cond, "qti-response-if")
    cond_children_factory(r_if)
    sv = _sub(r_if, "qti-set-outcome-value", identifier="SCORE")
    _sub(sv, "qti-base-value", "1", **{"base-type": "float"})
    r_else = _sub(cond, "qti-response-else")
    sv = _sub(r_else, "qti-set-outcome-value", identifier="SCORE")
    _sub(sv, "qti-base-value", "0", **{"base-type": "float"})


def item_to_qti(item: Item) -> bytes:
    root = etree.Element(_q("qti-assessment-item"), nsmap={None: QTI_NS, "xsi": XSI_NS})
    root.set("identifier", item.id)
    root.set("title", item.provenance.get("title", item.template))
    root.set("adaptive", "false")
    root.set("time-dependent", "false")
    root.set(f"{{{XML_NS}}}lang", "es-AR")

    base = {"choice": "identifier", "numeric": "float", "expression": "string", "open": "string"}[item.kind]
    rd = _sub(root, "qti-response-declaration", identifier="RESPONSE", cardinality="single", **{"base-type": base})
    if item.kind != "open":
        cr = _sub(rd, "qti-correct-response")
        _sub(cr, "qti-value", str(item.correct))
    od = _sub(root, "qti-outcome-declaration", identifier="SCORE", cardinality="single", **{"base-type": "float"})
    _sub(od, "qti-default-value").append(etree.Element(_q("qti-value")))
    od[0][0].text = "0"

    body = _sub(root, "qti-item-body")
    stim = item.stimulus
    if stim and stim.get("type") == "rect":
        _sub(body, "p", f"Figura: rectángulo de {stim['width']} {stim['unit']} por {stim['height']} {stim['unit']}.")
    elif stim:
        if stim["type"] in ("bar_chart", "line_chart"):          # el gráfico se exporta como su tabla de datos
            header = [stim.get("x_label", ""), stim.get("y_label", "")]
            rows = [[c, str(v)] for c, v in zip(stim["categories"], stim["values"])]
            _sub(body, "p", f"Datos del gráfico: {stim.get('title', '')}.")
        else:
            header, rows = stim["header"], stim["rows"]
        table = _sub(body, "table")
        tr = _sub(_sub(table, "thead"), "tr")
        for h in header:
            _sub(tr, "th", h)
        tb = _sub(table, "tbody")
        for row in rows:
            tr = _sub(tb, "tr")
            for cell in row:
                _sub(tr, "td", cell)

    if item.kind == "choice":
        ci = _sub(body, "qti-choice-interaction", **{"response-identifier": "RESPONSE", "shuffle": "true", "max-choices": "1"})
        _sub(ci, "qti-prompt", item.stem)
        for o in item.options:
            _sub(ci, "qti-simple-choice", o.text, identifier=o.id)
    else:
        _sub(body, "p", item.stem)
        _sub(_sub(body, "p"), "qti-text-entry-interaction",
             **{"response-identifier": "RESPONSE", "expected-length": "12",
                "class": "math-input" if item.kind == "expression" else "numeric-input"})

    rp = _sub(root, "qti-response-processing")
    if item.kind == "choice":
        def cond(r_if):
            m = _sub(r_if, "qti-match")
            _sub(m, "qti-variable", identifier="RESPONSE")
            _sub(m, "qti-correct", identifier="RESPONSE")
        _score_block(rp, cond)
    elif item.kind == "numeric":
        def cond(r_if):
            eq = _sub(r_if, "qti-equal", **{"tolerance-mode": "absolute", "tolerance": str(item.tolerance)})
            _sub(eq, "qti-variable", identifier="RESPONSE")
            _sub(eq, "qti-correct", identifier="RESPONSE")
        _score_block(rp, cond)
    # expression/open: la equivalencia simbólica la resuelve el servicio de corrección (ver scoring.py)
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

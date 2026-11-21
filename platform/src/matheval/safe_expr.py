"""Lectura segura de expresiones algebraicas escritas por estudiantes.

No usa eval ni parse_expr de SymPy: valida con lista blanca de caracteres, recorre el AST
permitiendo solo aritmética básica y variables declaradas, y limita tamaño y exponentes.
"""
from __future__ import annotations
import ast
import re
import sympy as sp

ALLOWED_RE = re.compile(r"^[0-9A-Za-z+\-*/^().,\s×·]+$")
MAX_LEN = 80
MAX_NODES = 60
MAX_EXP = 6


class UnsafeExpression(ValueError):
    pass


def _preprocess(s: str) -> str:
    s = s.strip().replace("×", "*").replace("·", "*")
    s = re.sub(r"\b[1-9]\d{0,2}(?:\.\d{3})+(?!\d)", lambda m: m.group(0).replace(".", ""), s)
    s = s.replace(",", ".").replace("^", "**")
    s = re.sub(r"(\d)\s*([A-Za-z(])", r"\1*\2", s)
    s = re.sub(r"(\))\s*([A-Za-z0-9(])", r"\1*\2", s)
    s = re.sub(r"([A-Za-z])\s*\(", r"\1*(", s)
    return s


def to_sympy(text: str, variables=("n",)) -> sp.Expr:
    if not isinstance(text, str) or len(text) > MAX_LEN or not ALLOWED_RE.match(text):
        raise UnsafeExpression("expresión no permitida")
    try:
        tree = ast.parse(_preprocess(text), mode="eval")
    except SyntaxError as e:
        raise UnsafeExpression("sintaxis inválida") from e
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise UnsafeExpression("expresión demasiado larga")
    syms = {v: sp.Symbol(v) for v in variables}

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if abs(node.value) > 10**9:
                raise UnsafeExpression("número fuera de rango")
            return sp.Rational(str(node.value))
        if isinstance(node, ast.Name):
            if node.id in syms:
                return syms[node.id]
            raise UnsafeExpression(f"nombre no permitido: {node.id}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = ev(node.operand)
            return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            l, r = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add):
                return l + r
            if isinstance(node.op, ast.Sub):
                return l - r
            if isinstance(node.op, ast.Mult):
                return l * r
            if isinstance(node.op, ast.Div):
                if r == 0:
                    raise UnsafeExpression("división por cero")
                return l / r
            if isinstance(node.op, ast.Pow):
                if not (r.is_Integer and abs(int(r)) <= MAX_EXP):
                    raise UnsafeExpression("exponente no permitido")
                return l ** r
        raise UnsafeExpression("elemento no permitido")

    return ev(tree)


def equivalent(a: str, b: str, variables=("n",)) -> bool:
    try:
        return sp.simplify(to_sympy(a, variables) - to_sympy(b, variables)) == 0
    except (UnsafeExpression, ZeroDivisionError, TypeError):
        return False

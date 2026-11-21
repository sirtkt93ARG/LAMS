"""Taxonomía de habilidades (Q-matriz plantilla -> habilidades) y prerrequisitos."""
from __future__ import annotations

SKILLS: dict[str, tuple[str, list[str]]] = {
    "operaciones_enteros": ("Operaciones con números enteros", []),
    "lectura_tablas": ("Lectura de tablas", []),
    "lectura_graficos": ("Lectura de gráficos", ["lectura_tablas"]),
    "porcentajes": ("Porcentajes", ["operaciones_enteros"]),
    "proporcionalidad": ("Proporcionalidad", ["operaciones_enteros"]),
    "escalas_medidas": ("Escalas y medidas", ["proporcionalidad"]),
    "perimetro_area": ("Perímetro y área", ["operaciones_enteros"]),
    "teorema_pitagoras": ("Teorema de Pitágoras", ["perimetro_area"]),
    "estadistica_descriptiva": ("Promedio y mediana", ["operaciones_enteros", "lectura_tablas"]),
    "probabilidad": ("Probabilidad", ["porcentajes", "lectura_tablas"]),
    "expresiones_algebraicas": ("Expresiones algebraicas", ["operaciones_enteros"]),
    "funciones_lineales": ("Funciones lineales", ["expresiones_algebraicas"]),
    "ecuaciones_sistemas": ("Ecuaciones y sistemas", ["expresiones_algebraicas"]),
    "patrones_generalizacion": ("Patrones y generalización", ["expresiones_algebraicas"]),
    "conteo_sistematico": ("Conteo sistemático", ["operaciones_enteros"]),
}

TEMPLATE_SKILLS: dict[str, list[str]] = {
    "T1": ["porcentajes"], "T2": ["lectura_tablas"], "T3": ["expresiones_algebraicas", "funciones_lineales"],
    "T4": ["escalas_medidas", "perimetro_area"], "T5": ["probabilidad"], "T6": ["funciones_lineales"],
    "T7": ["operaciones_enteros"], "T8": ["lectura_tablas"], "T9": ["operaciones_enteros"],
    "T10": ["conteo_sistematico"], "T11": ["patrones_generalizacion", "expresiones_algebraicas"],
    "T12": ["expresiones_algebraicas", "patrones_generalizacion"], "T13": ["lectura_graficos"],
    "T14": ["lectura_graficos"], "T15": ["perimetro_area"], "T16": ["proporcionalidad"], "T17": ["porcentajes"],
    "T18": ["estadistica_descriptiva"], "T19": ["estadistica_descriptiva"], "T20": ["funciones_lineales"],
    "T21": ["ecuaciones_sistemas"], "T22": ["teorema_pitagoras"], "T23": ["porcentajes"],
    "T24": ["proporcionalidad", "escalas_medidas"],
}


def skills_of_item(item_id: str) -> list[str]:
    return TEMPLATE_SKILLS.get(item_id.split("-")[0], [])


def templates_for(skill: str) -> list[str]:
    return [t for t, ss in TEMPLATE_SKILLS.items() if skill in ss]

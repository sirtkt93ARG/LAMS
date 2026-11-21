"""Rúbricas orientativas por competencia para respuestas abiertas.

Los descriptores son criterios formativos de apoyo, no baremos psicométricos ni
puntos de corte validados. Cada asignación guarda una copia inmutable del esquema.
"""
from __future__ import annotations

from .skills import SKILLS, skills_of_item

_LEVELS = {
    "interpretacion": {
        "label": "Interpretación",
        "descriptors": {
            "0": "No presenta evidencia interpretable sobre la consigna.",
            "1": "Reconoce algún dato o elemento, pero confunde su significado o relevancia.",
            "2": "Identifica parte de la información relevante; la interpretación es incompleta.",
            "3": "Interpreta correctamente los datos y las relaciones necesarias para la competencia.",
            "4": "Integra datos, relaciones y condiciones; justifica qué información es relevante y por qué.",
        },
    },
    "estrategia": {
        "label": "Estrategia",
        "descriptors": {
            "0": "No propone una estrategia relacionada con la tarea.",
            "1": "Ensaya una acción aislada sin una secuencia pertinente.",
            "2": "Elige una estrategia parcialmente adecuada, pero no la desarrolla de forma consistente.",
            "3": "Selecciona y aplica una estrategia adecuada para resolver la tarea.",
            "4": "Selecciona, compara o adapta estrategias y explica por qué la elegida es eficiente.",
        },
    },
    "desarrollo_validacion": {
        "label": "Desarrollo y validación",
        "descriptors": {
            "0": "No hay desarrollo verificable ni conclusión.",
            "1": "El desarrollo contiene errores que impiden sostener la conclusión.",
            "2": "El procedimiento es parcialmente correcto; quedan errores o pasos sin justificar.",
            "3": "Desarrolla un procedimiento correcto y obtiene una conclusión coherente.",
            "4": "Desarrolla, justifica y comprueba el resultado; reconoce límites o verifica con otra vía.",
        },
    },
}


def competencies_for_item(item_id: str) -> list[dict]:
    """Competencias vinculadas al mapa Q del banco, en orden estable."""
    return [
        {"id": skill, "name": SKILLS[skill][0]}
        for skill in skills_of_item(item_id)
        if skill in SKILLS
    ]


def rubric_snapshot(skill_id: str) -> dict | None:
    """Devuelve una copia JSON-serializable que puede persistirse con la asignación."""
    if skill_id not in SKILLS:
        return None
    name = SKILLS[skill_id][0]
    return {
        "version": 1,
        "competency_id": skill_id,
        "competency": name,
        "focus": f"Valorar cómo el estudiante interpreta, aborda y valida una tarea de {name.lower()}.",
        "criteria": [
            {"id": key, "label": value["label"], "descriptors": dict(value["descriptors"])}
            for key, value in _LEVELS.items()
        ],
        "scale": {"min": 0, "max": 4, "meaning": "0 = sin evidencia; 4 = desempeño sólido y transferible"},
        "notice": "Rúbrica orientativa para retroalimentación docente; no equivale a una escala calibrada.",
    }


def valid_competency_for_item(item_id: str, skill_id: str) -> bool:
    return skill_id in {entry["id"] for entry in competencies_for_item(item_id)}

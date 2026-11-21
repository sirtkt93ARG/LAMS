"""Escala propia N1-N8. Los puntos de corte son MARCADORES hasta que se calibren con datos de piloto
y un estudio de establecimiento de puntos de corte. No son equivalentes a los niveles de PISA."""
from __future__ import annotations

# Separaciones de 0,7 en la escala theta; N4 = hipótesis de nivel mínimo.
PLACEHOLDER_CUTS = [-2.1, -1.4, -0.7, 0.0, 0.7, 1.4, 2.1]

DESCRIPTORS = {
    1: "Responde preguntas de un solo paso con toda la información a la vista y presentada de forma simple",
    2: "Opera con números enteros siguiendo instrucciones explícitas",
    3: "Repite o encadena procedimientos rutinarios en contextos explícitos",
    4: "Elige una estrategia sencilla, toma datos de una tabla o gráfico y comunica el resultado en el contexto",
    5: "Combina varios pasos y representaciones, y opera con porcentajes, fracciones y proporciones",
    6: "Usa modelos dados para situaciones con dos variables, verifica la razonabilidad y explica su razonamiento",
    7: "Construye modelos propios, declara supuestos y planifica estrategias sistemáticas",
    8: "Generaliza y justifica en situaciones nuevas y abiertas, y evalúa los límites del modelo",
}
BASELINE_LEVEL = 4  # hipótesis de nivel mínimo de competencia

# Correspondencia con categorías locales: SOLO marcador, requiere estudio de puntos de corte.
PLACEHOLDER_LOCAL_MAP = {1: "por_debajo_del_basico", 2: "por_debajo_del_basico", 3: "por_debajo_del_basico",
                         4: "basico", 5: "satisfactorio", 6: "satisfactorio", 7: "avanzado", 8: "avanzado"}


def level_of(theta: float, cuts=PLACEHOLDER_CUTS) -> int:
    return 1 + sum(theta >= c for c in cuts)


def prior_difficulty(level: int, spacing: float = 0.7) -> float:
    """Dificultad a priori (solo para práctica, nunca para medir) a partir del nivel objetivo."""
    return (level - 4.5) * spacing

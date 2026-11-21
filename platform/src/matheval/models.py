from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    BORRADOR = "borrador"
    VERIFICADO = "verificado"
    REVISADO = "revisado"
    PILOTO = "piloto"
    CALIBRADO = "calibrado"
    OPERATIVO = "operativo"
    RECHAZADO = "rechazado"


STATUS_ORDER = [s for s in Status if s is not Status.RECHAZADO]


class Axis(str, Enum):
    NUMEROS = "numeros_algebra"
    FUNCIONES = "funciones_relaciones"
    GEOMETRIA = "geometria_medida"
    DATOS = "datos_azar"


class Process(str, Enum):
    MODELIZAR = "modelizar"
    RESOLVER = "resolver"
    INTERPRETAR = "interpretar"
    ARGUMENTAR = "argumentar"


class Context(str, Enum):
    COTIDIANO = "cotidiano"
    SOCIAL = "social"
    LABORAL = "laboral_economico"
    CIENTIFICO = "cientifico"


@dataclass
class Option:
    id: str
    text: str
    tag: str | None = None  # etiqueta diagnóstica del error que modela el distractor


@dataclass
class IRTParams:
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0


@dataclass
class Item:
    id: str
    template: str
    stem: str
    kind: str  # choice | numeric | expression | open
    correct: Any
    axis: Axis
    process: Process
    context: Context
    target_level: int
    options: list[Option] = field(default_factory=list)
    stimulus: dict | None = None
    tolerance: float = 0.0
    variables: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    status: Status = Status.VERIFICADO
    provenance: dict = field(default_factory=dict)
    license: str = "propia"
    irt: IRTParams | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "template": self.template, "stem": self.stem, "kind": self.kind,
            "correct": self.correct, "axis": self.axis.value, "process": self.process.value,
            "context": self.context.value, "target_level": self.target_level,
            "options": [{"id": o.id, "text": o.text, "tag": o.tag} for o in self.options],
            "stimulus": self.stimulus, "tolerance": self.tolerance, "variables": self.variables,
            "params": self.params, "status": self.status.value, "provenance": self.provenance,
            "license": self.license,
            "irt": None if self.irt is None else {"a": self.irt.a, "b": self.irt.b, "c": self.irt.c},
        }

    @staticmethod
    def from_dict(d: dict) -> "Item":
        irt = d.get("irt")
        return Item(
            id=d["id"], template=d["template"], stem=d["stem"], kind=d["kind"], correct=d["correct"],
            axis=Axis(d["axis"]), process=Process(d["process"]), context=Context(d["context"]),
            target_level=d["target_level"],
            options=[Option(**o) for o in d.get("options", [])],
            stimulus=d.get("stimulus"), tolerance=d.get("tolerance", 0.0),
            variables=d.get("variables", []), params=d.get("params", {}),
            status=Status(d.get("status", "verificado")), provenance=d.get("provenance", {}),
            license=d.get("license", "propia"),
            irt=None if not irt else IRTParams(**irt),
        )

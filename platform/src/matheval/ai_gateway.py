"""Pasarela de IA agnóstica de proveedor. Reglas: sin datos personales en prompts, sin chat libre con
estudiantes, y todo texto generado entra como borrador con procedencia registrada."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Protocol

PROMPT_VERSION = "contextos-v1"
_PII = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
        (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}\b"), "[documento]"),
        (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[telefono]")]


def redact_pii(text: str) -> str:
    for rx, rep in _PII:
        text = rx.sub(rep, text)
    return text


class LLMProvider(Protocol):
    name: str

    def complete(self, system: str, prompt: str, max_tokens: int = 400) -> str: ...


@dataclass
class DraftContext:
    template_id: str
    text: str
    provenance: dict


class ContextDrafter:
    """Propone redacciones de contexto para una plantilla. Nunca publica: devuelve borradores."""
    SYSTEM = ("Sos un redactor de problemas de matemática para estudiantes de 15 años de Argentina. "
              "Escribí contextos breves, neutros y sin datos personales. No incluyas números ni respuestas.")

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def draft(self, template_id: str, theme: str, n: int = 3) -> list[DraftContext]:
        prompt = redact_pii(f"Plantilla {template_id}. Tema: {theme}. Proponé {n} contextos, uno por línea.")
        raw = self.provider.complete(self.SYSTEM, prompt)
        lines = [l.strip(" -•\t") for l in raw.splitlines() if l.strip()][:n]
        return [DraftContext(template_id, l, {"method": "ia", "model": self.provider.name,
                                              "prompt_version": PROMPT_VERSION, "status": "borrador"}) for l in lines]


class MockProvider:
    name = "mock"

    def complete(self, system: str, prompt: str, max_tokens: int = 400) -> str:
        return "- Una cooperativa de bicicletas del barrio\n- Un club que alquila canchas\n- Una biblioteca que presta libros"

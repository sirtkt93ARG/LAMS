"""Banco de ítems con control de estados: solo ítems calibrados miden; IA nunca pasa sin revisión humana."""
from __future__ import annotations
import json
from pathlib import Path
from .models import Item, Status, STATUS_ORDER


class BankError(Exception):
    pass


class ItemBank:
    def __init__(self, items: list[Item] | None = None):
        self.items: dict[str, Item] = {i.id: i for i in (items or [])}

    def add(self, item: Item) -> None:
        if item.provenance.get("method") == "ia" and item.status.value in ("revisado", "piloto", "calibrado", "operativo"):
            if not item.provenance.get("reviewed_by"):
                raise BankError("un ítem generado con IA requiere reviewed_by para superar el estado borrador")
        self.items[item.id] = item

    def promote(self, item_id: str, to: Status, *, reviewed_by: str | None = None) -> None:
        it = self.items[item_id]
        if it.status not in STATUS_ORDER or to not in STATUS_ORDER:
            raise BankError("transición inválida desde o hacia rechazado")
        if STATUS_ORDER.index(to) != STATUS_ORDER.index(it.status) + 1:
            raise BankError(f"transición inválida {it.status.value} -> {to.value}")
        if to == Status.REVISADO:
            if not reviewed_by:
                raise BankError("pasar a revisado exige un revisor")
            it.provenance["reviewed_by"] = reviewed_by
        if to == Status.CALIBRADO and it.irt is None:
            raise BankError("pasar a calibrado exige parámetros IRT")
        it.status = to

    def pool(self, mode: str) -> list[Item]:
        if mode == "medicion":
            ok = {Status.CALIBRADO, Status.OPERATIVO}
        elif mode == "practica":
            ok = {Status.REVISADO, Status.PILOTO, Status.CALIBRADO, Status.OPERATIVO}
        elif mode == "piloto":
            ok = {Status.REVISADO, Status.PILOTO}
        else:
            raise BankError("modo desconocido")
        return [i for i in self.items.values() if i.status in ok and "NC" not in i.license.upper().split("-")]

    def dump(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for i in self.items.values():
                f.write(json.dumps(i.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def load(path: str | Path) -> "ItemBank":
        with open(path, encoding="utf-8") as f:
            return ItemBank([Item.from_dict(json.loads(l)) for l in f if l.strip()])

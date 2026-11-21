"""Sentencias xAPI 1.0.x con identificadores seudónimos y envío a un LRS (Ralph u otro)."""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import uuid
import urllib.request
from datetime import datetime, timezone

VERB_ANSWERED = {"id": "http://adlnet.gov/expapi/verbs/answered", "display": {"es-AR": "respondió"}}
VERB_COMPLETED = {"id": "http://adlnet.gov/expapi/verbs/completed", "display": {"es-AR": "completó"}}
EXT = "https://matheval.example/xapi/ext/"  # reemplazar por el dominio propio del producto


def pseudonymize(student_id: str, tenant_secret: bytes) -> str:
    """Identificador estable y no reversible: el LRS nunca recibe el identificador real."""
    return hmac.new(tenant_secret, student_id.encode(), hashlib.sha256).hexdigest()[:32]


def answered_statement(*, pid: str, tenant_home: str, item_id: str, item_title: str, response: str,
                       score: float | None, success: bool | None, level_target: int, axis: str,
                       process: str, tag: str | None, duration_s: float | None = None, now=None) -> dict:
    stmt = {
        "id": str(uuid.uuid4()),
        "actor": {"objectType": "Agent", "account": {"homePage": tenant_home, "name": pid}},
        "verb": VERB_ANSWERED,
        "object": {"objectType": "Activity", "id": f"{tenant_home.rstrip('/')}/items/{item_id}",
                   "definition": {"type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                  "name": {"es-AR": item_title}}},
        "result": {"response": response, "success": success,
                   "score": {"raw": score, "min": 0, "max": 1} if score is not None else None},
        "context": {"extensions": {EXT + "target_level": level_target, EXT + "axis": axis,
                                   EXT + "process": process, EXT + "error_tag": tag}},
        "timestamp": (now or datetime.now(timezone.utc)).isoformat(),
    }
    if duration_s is not None:
        stmt["result"]["duration"] = f"PT{duration_s:.1f}S"
    stmt["result"] = {k: v for k, v in stmt["result"].items() if v is not None}
    return stmt


def post_statements(lrs_url: str, statements: list[dict], user: str, password: str, timeout: float = 10.0) -> int:
    req = urllib.request.Request(
        lrs_url.rstrip("/") + "/xAPI/statements", data=json.dumps(statements).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Experience-API-Version": "1.0.3",
                 "Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310 (URL de configuración propia)
        return r.status

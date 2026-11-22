"""API del motor de evaluación. Capa fina sobre `matheval`. Las sesiones, respuestas, revisiones, consentimiento y
auditoría se guardan con `Store` (SQLite en desarrollo, PostgreSQL con RLS en producción). Solo se persiste el
seudónimo del usuario; el identificador real vive en el LMS."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
import urllib.request
import uuid
from collections import Counter, defaultdict
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from matheval import templates as TPL
from matheval.adaptive import MSTSession, PoolItem, build_design
from matheval.analytics import family_stats
from matheval.bank import ItemBank
from matheval.directed import DirectedSession, FormSession, build_catalog, build_form, start_directed
from matheval.explain import explain
from matheval.levels import BASELINE_LEVEL, DESCRIPTORS, level_of, prior_difficulty
from matheval.mastery import P_INIT, compute_mastery, recommend, summary
from matheval.models import IRTParams, Status
from matheval.observatory import analytics as OA
from matheval.observatory.data import AVG_NAME, DOMAINS, load_csv, load_gaps
from matheval.scoring import score_response
from matheval.skills import SKILLS
from matheval.rubrics import competencies_for_item, rubric_snapshot, valid_competency_for_item
from matheval.xapi import answered_statement, post_statements, pseudonymize
from .auth import DEV, User, current_user, mint_session_token, set_token_consumer, verify_handoff
from .limits import RateLimiter
from .review import CHECKLIST, REQUIRED, apply_calibration, apply_reviews, scope_of, template_status
from .security import check_config
from .store import Store

log = logging.getLogger("matheval")
_config_errors, _config_warnings = check_config(os.environ, DEV)
for _warning in _config_warnings:
    log.warning("configuración: %s", _warning)
if _config_errors:
    raise RuntimeError("Configuración insegura: " + "; ".join(_config_errors))
app = FastAPI(title="matheval API", version="0.7.0")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000")],
                   allow_methods=["*"], allow_headers=["*"])
BANK = ItemBank.load(os.getenv("BANK_PATH", "data/bank_demo.jsonl"))
OBS = load_csv(os.getenv("OBSERVATORY_PATH", "data/observatory/pisa_agregados.csv"))
GAPS = load_gaps(os.getenv("OBSERVATORY_GAPS_PATH", "data/observatory/pisa_brechas.csv"))
STORE = Store(os.getenv("DATABASE_URL", "sqlite:///data/matheval.db"))
set_token_consumer(STORE.consume_token)
apply_reviews(BANK, STORE)
apply_calibration(BANK, os.getenv("CALIBRATION_PATH", "data/calibration.json"))
SECRET = os.getenv("PSEUDONYM_SECRET", "cambiar-en-produccion").encode()
LRS_URL, LRS_USER, LRS_PASS = os.getenv("LRS_URL"), os.getenv("LRS_USER", ""), os.getenv("LRS_PASS", "")
LTI_SERVICE_URL = os.getenv("LTI_SERVICE_URL")
REQUIRE_CONSENT = os.getenv("REQUIRE_CONSENT", "0" if DEV else "1") == "1"
LADDER = [{"level": k, "descriptor": DESCRIPTORS[k]} for k in sorted(DESCRIPTORS)]
MODES = ("practica", "medicion", "dirigida", "piloto")
LIM, METRICS = RateLimiter(STORE), Counter()


@app.middleware("http")
async def observe(request, call_next):
    rid, t0 = request.headers.get("x-request-id") or uuid.uuid4().hex[:12], time.perf_counter()
    response = await call_next(request)
    METRICS["requests_total"] += 1
    METRICS[f"responses_{response.status_code // 100}xx"] += 1
    response.headers["X-Request-ID"] = rid
    log.info(json.dumps({"rid": rid, "method": request.method, "path": request.url.path, "status": response.status_code,
                         "ms": round((time.perf_counter() - t0) * 1000, 1)}))
    return response


# ---- utilidades --------------------------------------------------------------------
def _pid(user: User) -> str:
    return pseudonymize(user.sub, SECRET + user.tenant_id.encode())


def _student_key(sub: str, tenant: str) -> str:
    pid = pseudonymize(sub, SECRET + tenant.encode())
    return hashlib.sha256(pid.encode()).hexdigest()


def _nrps_names(user: User) -> dict[str, str]:
    """Consulta nombres en vivo al LMS; no persiste roster ni datos personales."""
    if not user.nrps or not LTI_SERVICE_URL:
        return {}
    try:
        req = urllib.request.Request(
            LTI_SERVICE_URL.rstrip("/") + "/lti/nrps/roster",
            data=json.dumps({"nrps": user.nrps}).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-Internal-Secret": os.getenv("LTI_HANDOFF_SECRET", "")},
        )
        with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310 (servicio interno configurado)
            members = json.loads(response.read()).get("members", [])
        return {
            _student_key(member["user_id"], user.tenant_id): member["name"]
            for member in members
            if isinstance(member, dict) and isinstance(member.get("user_id"), str)
            and isinstance(member.get("name"), str) and member["name"].strip()
        }
    except Exception:  # noqa: BLE001
        log.warning("no se pudo consultar el roster NRPS; se mantienen los seudónimos")
        return {}


def _post_xapi_if_not_erased(tenant: str, pid: str, lrs_url: str, statements: list[dict],
                             user: str, password: str) -> bool:
    """Envía xAPI bajo el mismo bloqueo durable que usa la supresión del alumno."""
    return STORE.run_if_xapi_export_allowed(
        tenant, pid, lambda: post_statements(lrs_url, statements, user, password)
    )


def _pool(mode: str):
    bank_mode = "practica" if mode in ("dirigida", "piloto") else mode
    # Los ítems abiertos requieren corrección manual; no se pueden administrar en CAT/MST.
    items = [i for i in BANK.pool(bank_mode) if i.kind != "open"]
    if DEV and bank_mode == "practica":                                  # solo desarrollo: permite ítems solo verificados
        items += [i for i in BANK.items.values()
                  if i.status == Status.VERIFICADO and i.kind != "open"]
    return items


def _params(item, mode: str) -> IRTParams:
    if mode == "medicion":
        return item.irt
    return IRTParams(1.0, prior_difficulty(item.target_level), 0.25 if item.kind == "choice" else 0.0)


def _public(item) -> dict:
    """Vista para el estudiante: nunca incluye clave, etiquetas de error ni parámetros."""
    return {"id": item.id, "stem": item.stem, "kind": item.kind, "stimulus": item.stimulus,
            "options": [{"id": o.id, "text": o.text} for o in item.options]}


def _throttle(key: str, limit: int, window: float = 60.0) -> None:
    if not LIM.allow(key, limit, window):
        raise HTTPException(429, "demasiadas solicitudes: esperá unos segundos")


def _engine(snap: dict):
    kind = snap.get("kind", "mst")
    if kind == "piloto":
        return FormSession.from_snapshot(snap)
    if kind == "dirigida":
        return DirectedSession.from_snapshot(snap, build_catalog(_pool("dirigida"), snap["skill"]))
    return MSTSession.from_snapshot(snap)


def _load(sid: str, user: User) -> dict:
    row = STORE.load_session(sid, user.tenant_id)
    if not row or (user.role == "student" and row["pid"] != _pid(user)):
        raise HTTPException(404, "sesión no encontrada")
    st = row["state"]
    return {"mode": row["mode"], "version": row["version"], "total": st["total"], "tags": st["tags"], "hints": st.get("hints", {}), "eng": _engine(st["snap"])}


def _state_of(s: dict) -> dict:
    return {"total": s["total"], "tags": s["tags"], "hints": s["hints"], "snap": s["eng"].snapshot()}


def _state(s: dict) -> dict:
    e = s["eng"]
    return {"done": e.done, "answered": len(e.administered), "total": s["total"], "mode": s["mode"],
            "items": [] if e.done else [_public(BANK.items[i]) for i in e.next_items()]}


def _report(s: dict) -> dict:
    e = s["eng"]
    theta, se = e.estimate()
    lv = level_of(theta)
    base = {"kind": getattr(e, "kind", "mst"), "theta": round(theta, 2), "se": round(se, 2), "level": lv,
            "descriptor": DESCRIPTORS[lv], "at_or_above_baseline": lv >= BASELINE_LEVEL, "answered": len(e.administered),
            "error_tags": dict(Counter(t for t in s["tags"] if t)), "ladder": LADDER, "preliminary": s["mode"] != "medicion",
            "note": "Niveles preliminares: los puntos de corte se definirán con datos de piloto."}
    if base["kind"] == "dirigida":
        wrong = [r[0] for r in e.responses if not r[1]][:5]
        base.update({"skill": e.skill, "skill_name": SKILLS[e.skill][0], "correct": sum(r[1] for r in e.responses),
                     "mistakes": [{"stem": BANK.items[i].stem, "answer": BANK.items[i].params["answer_text"],
                                   "steps": explain(BANK.items[i])["steps"]} for i in wrong if i in BANK.items]})
    return base


def _consent_gate(user: User) -> None:
    if REQUIRE_CONSENT and not STORE.tenant_settings(user.tenant_id)["consent_attested_at"]:
        raise HTTPException(403, "La escuela todavía no confirmó el consentimiento de las familias. Avisale a tu docente.")


def _send_grade(user: User, result: dict, mode: str) -> None:
    """Devuelve la nota al libro de calificaciones del LMS (LTI Advantage) a través del servicio LTI."""
    if not (LTI_SERVICE_URL and user.ags):
        return
    body = {**{k: user.ags[k] for k in ("iss", "client_id", "lineitem")}, "user_id": user.sub, "score_given": result["level"],
            "score_maximum": 8, "comment": f"Nivel N{result['level']}" + (" (preliminar)" if mode != "medicion" else "")}
    req = urllib.request.Request(LTI_SERVICE_URL.rstrip("/") + "/lti/ags/score", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Internal-Secret": os.getenv("LTI_HANDOFF_SECRET", "")})
    try:
        urllib.request.urlopen(req, timeout=10)                                   # noqa: S310
    except Exception:                                                              # noqa: BLE001
        log.exception("no se pudo devolver la nota al LMS")


class StartIn(BaseModel):
    mode: str = "practica"          # practica | medicion | dirigida | piloto
    skill: str | None = None        # solo para dirigida


class AnswerIn(BaseModel):
    item_id: str
    response: str = ""
    duration_s: float | None = None


class ExchangeIn(BaseModel):
    token: str


class ReviewIn(BaseModel):
    decision: str
    comment: str = ""
    checklist: dict = {}


class NetworkInviteIn(BaseModel):
    tenant_id: str

class OpenAssignmentIn(BaseModel):
    item_id: str
    title: str
    instructions: str = ""
    course_id: str | None = None
    due_at: str | None = None
    competency_id: str | None = None


class OpenSubmissionIn(BaseModel):
    response: str


class OpenGradeIn(BaseModel):
    score: float
    feedback: str = ""
    rubric: dict = {}


# ---- acceso ------------------------------------------------------------------------
@app.post("/v1/lti/exchange")
def lti_exchange(body: ExchangeIn):
    """Cambia el token de 60 s del servicio LTI por una sesión de 2 horas."""
    _throttle("exchange", 600)
    u = verify_handoff(body.token)
    return {"access_token": mint_session_token(u), "role": u.role}


# ---- estudiantes -------------------------------------------------------------------
@app.post("/v1/sessions")
def start(body: StartIn, user: User = Depends(current_user)):
    if user.role != "student":
        raise HTTPException(403, "solo estudiantes")
    if body.mode not in MODES:
        raise HTTPException(400, "modo inválido")
    _consent_gate(user)
    # Las decisiones de curaduría viven en la base; cada worker refresca el banco antes de crear una sesión.
    apply_reviews(BANK, STORE)
    pid = _pid(user)
    if body.mode in ("practica", "medicion"):
        pool = [PoolItem(i.id, i.axis.value, _params(i, body.mode), i.provenance.get("fp")) for i in _pool(body.mode)]
        if len(pool) < 56:
            raise HTTPException(409, "el banco no tiene ejercicios aprobados suficientes para este modo")
        design = build_design(pool, rng=random.Random())
        eng = MSTSession(design, {p.id: p.params for p in pool})
        total = len(design.stage1) + len(design.stage2["mid"]) + len(design.stage3["mid"])
    elif body.mode == "dirigida":
        if body.skill not in SKILLS:
            raise HTTPException(400, "habilidad desconocida")
        cat = build_catalog(_pool("dirigida"), body.skill)
        if not cat["levels"]:
            raise HTTPException(409, "todavía no hay ejercicios aprobados para este tema")
        st = compute_mastery(STORE.responses_for_pid(user.tenant_id, pid)).get(body.skill)
        lo, hi = min(cat["levels"]), max(cat["levels"])
        eng = start_directed(body.skill, cat, max(lo, min(hi, round(2 + 5 * (st.p if st else P_INIT)))), 10, random.randrange(1 << 30))
        total = 10
    else:
        ids, params = build_form(_pool("piloto"), random.randrange(1 << 30))
        if len(ids) < 12:
            raise HTTPException(409, "el banco no tiene plantillas aprobadas suficientes")
        eng, total = FormSession(ids, params), len(ids)
    s = {"mode": body.mode, "tags": [], "hints": {}, "eng": eng, "total": total}
    sid = str(uuid.uuid4())
    STORE.create_session(sid, user.tenant_id, pid, body.mode, _state_of(s), user.course_id, user.course_label)
    return {"session_id": sid, **_state(s)}


@app.get("/v1/sessions/{sid}/items")
def pending(sid: str, user: User = Depends(current_user)):
    return _state(_load(sid, user))


@app.get("/v1/sessions/{sid}/hint")
def hint(sid: str, item_id: str, level: int = 1, user: User = Depends(current_user)):
    _throttle(f"hint:{user.tenant_id}:{user.sub}", 60)
    s = _load(sid, user)
    if s["mode"] != "dirigida":
        raise HTTPException(403, "las pistas solo están disponibles en la práctica por tema")
    if item_id not in s["eng"].next_items():
        raise HTTPException(409, "ítem no pendiente")
    level = max(1, min(2, level))
    s["hints"][item_id] = max(level, s["hints"].get(item_id, 0))
    if not STORE.save_session(sid, user.tenant_id, _state_of(s), expected_version=s["version"]):
        raise HTTPException(409, "La sesión cambió mientras pedías la pista. Actualizá la actividad e intentá de nuevo.")
    return {"level": level, "hint": explain(BANK.items[item_id])["hints"][level - 1]}


@app.post("/v1/sessions/{sid}/answers")
def answer(sid: str, body: AnswerIn, tasks: BackgroundTasks, user: User = Depends(current_user)):
    _throttle(f"ans:{user.tenant_id}:{user.sub}", 240)
    s = _load(sid, user)
    e = s["eng"]
    show = s["mode"] in ("practica", "dirigida")
    if body.item_id in e.administered:                       # reintento de red: responder lo mismo sin duplicar
        out = {**_state(s), "duplicate": True}
        if show:
            out["correct"] = bool(next(r[1] for r in e.responses if r[0] == body.item_id))
        return out
    if body.item_id not in e.next_items():
        raise HTTPException(409, "ejercicio no pendiente")
    item = BANK.items[body.item_id]
    if item.kind == "open":
        raise HTTPException(409, "Este ejercicio requiere corrección docente y no está habilitado en prácticas automáticas. Reiniciá la actividad.")
    res = score_response(item, body.response)
    hints = int(s["hints"].get(item.id, 0))
    e.record(item.id, int(res.score or 0))
    s["tags"].append(res.tag)
    result = None
    if e.done:
        theta, se = e.estimate()
        result = {"theta": round(theta, 3), "se": round(se, 3), "level": level_of(theta), "kind": getattr(e, "kind", "mst")}
    saved = STORE.record_answer(
        sid, user.tenant_id, s["version"], _state_of(s), item.id, res.normalized or "",
        res.score, res.tag, body.duration_s, hints, result
    )
    if not saved:
        latest = _load(sid, user)
        if body.item_id in latest["eng"].administered:
            duplicate = {**_state(latest), "duplicate": True}
            if show:
                duplicate["correct"] = bool(next(r[1] for r in latest["eng"].responses if r[0] == body.item_id))
            return duplicate
        raise HTTPException(409, "La sesión cambió mientras respondías. Actualizá la actividad antes de continuar.")
    if LRS_URL:
        stmt = answered_statement(pid=_pid(user), tenant_home=f"https://{user.tenant_id}.tenants.matheval.example",
                                  item_id=item.id, item_title=item.provenance.get("title", item.template),
                                  response=res.normalized or "", score=res.score, success=bool(res.score),
                                  level_target=item.target_level, axis=item.axis.value, process=item.process.value,
                                  tag=res.tag, duration_s=body.duration_s)
        tasks.add_task(_post_xapi_if_not_erased, user.tenant_id, _pid(user), LRS_URL, [stmt], LRS_USER, LRS_PASS)
    if result and s["mode"] in ("practica", "medicion"):
        tasks.add_task(_send_grade, user, result, s["mode"])
    out = _state(s)
    if show:
        out["correct"] = bool(res.score)
    if s["mode"] == "dirigida":
        out["explanation"] = explain(item)["steps"]
    return out


@app.get("/v1/sessions/{sid}/report")
def report(sid: str, user: User = Depends(current_user)):
    return _report(_load(sid, user))


@app.get("/v1/student/open-assignments")
def student_open_assignments(user: User = Depends(current_user)):
    if user.role != "student":
        raise HTTPException(403, "solo estudiantes")
    _consent_gate(user)
    assignments = STORE.open_assignments_for_student(user.tenant_id, user.course_id, _pid(user))
    for assignment in assignments:
        item = BANK.items.get(assignment["item_id"])
        assignment["item"] = _public(item) if item and item.kind == "open" else None
        due_at = assignment.get("due_at")
        if isinstance(due_at, datetime):
            due_at = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
        elif due_at:
            due_at = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
        assignment["expired"] = bool(due_at and due_at <= datetime.now(timezone.utc))
    return {"assignments": assignments}


@app.post("/v1/student/open-assignments/{assignment_id}/submit")
def student_open_submit(assignment_id: str, body: OpenSubmissionIn, user: User = Depends(current_user)):
    if user.role != "student":
        raise HTTPException(403, "solo estudiantes")
    _consent_gate(user)
    response = body.response.strip()
    if not response or len(response) > 20000:
        raise HTTPException(400, "La respuesta debe tener entre 1 y 20000 caracteres.")
    visible = {a["id"] for a in STORE.open_assignments_for_student(user.tenant_id, user.course_id, _pid(user))}
    if assignment_id not in visible:
        raise HTTPException(404, "actividad no encontrada")
    ok = STORE.submit_open_response(str(uuid.uuid4()), assignment_id, user.tenant_id, _pid(user), response)
    if not ok:
        if STORE.open_assignment_expired(user.tenant_id, assignment_id):
            raise HTTPException(410, "El plazo de entrega de esta actividad ya venció.")
        raise HTTPException(409, "Ya existe una entrega pendiente de corrección. Podrás enviar otro intento cuando el docente la corrija.")
    latest = next((a for a in STORE.open_assignments_for_student(user.tenant_id, user.course_id, _pid(user))
                   if a["id"] == assignment_id), {})
    attempt_number = latest.get("attempt_number")
    action = "respuesta_abierta_reentregada" if attempt_number and attempt_number > 1 else "respuesta_abierta_entregada"
    STORE.audit(user.tenant_id, _pid(user), action, assignment_id)
    return {"status": "pendiente", "attempt_number": attempt_number}


@app.get("/v1/student/open-assignments/{assignment_id}/history")
def student_open_submission_history(assignment_id: str, user: User = Depends(current_user)):
    if user.role != "student":
        raise HTTPException(403, "solo estudiantes")
    _consent_gate(user)
    visible = {a["id"] for a in STORE.open_assignments_for_student(user.tenant_id, user.course_id, _pid(user))}
    if assignment_id not in visible:
        raise HTTPException(404, "actividad no encontrada")
    return {"attempts": STORE.open_submission_history_for_student(user.tenant_id, assignment_id, _pid(user))}


@app.get("/v1/student/open-submissions/{submission_id}")
def student_open_result(submission_id: str, user: User = Depends(current_user)):
    if user.role != "student":
        raise HTTPException(403, "solo estudiantes")
    result = STORE.open_submission_for_student(user.tenant_id, submission_id, _pid(user))
    if not result:
        raise HTTPException(404, "entrega no encontrada")
    return result


@app.get("/v1/me/progress")
def progress(user: User = Depends(current_user)):
    pid = _pid(user)
    rows = STORE.responses_for_pid(user.tenant_id, pid)
    states = compute_mastery(rows)
    return {"sessions": [{"id": x["id"], "mode": x["mode"], "level": (x["result"] or {}).get("level"), "finished_at": x["finished_at"]}
                         for x in STORE.sessions_of(user.tenant_id, pid)],
            "mastery": summary(states), "recommended": recommend(states), "responses": len(rows)}


@app.delete("/v1/me/data")
def delete_my_data(user: User = Depends(current_user)):
    """Elimina datos locales; si hay un LRS externo, informa que su supresión requiere acción del proveedor."""
    pid = _pid(user)
    out = STORE.delete_learner(user.tenant_id, pid, actor=user.sub)
    result = {**out, "local_data_deleted": True, "future_xapi_exports_blocked": True, "suppression_marker_retained": True}
    if LRS_URL:
        result["external_lrs"] = {
            "status": "manual_action_required",
            "agent": {
                "objectType": "Agent",
                "account": {
                    "homePage": f"https://{user.tenant_id}.tenants.matheval.example",
                    "name": pid,
                },
            },
            "message": (
                "Los Statements externos no se borraron. xAPI 1.0.3 no define su borrado: "
                "el administrador del LRS debe aplicar el procedimiento de supresión del proveedor."
            ),
        }
        result["erasure_complete"] = False
        return JSONResponse(status_code=202, content=result)
    result["external_lrs"] = {
        "status": "not_configured_currently",
        "message": (
            "No hay un LRS configurado en este momento. Si se utilizó uno anteriormente, "
            "la configuración actual no permite confirmar si quedan exportaciones históricas."
        ),
    }
    result["erasure_complete"] = None
    return result


# ---- docentes ----------------------------------------------------------------------
def _teacher(user: User) -> None:
    if user.role not in ("teacher", "admin"):
        raise HTTPException(403, "solo docentes")


def _curator(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(403, "solo administradores de contenido")


@app.get("/v1/teacher/courses")
def courses(user: User = Depends(current_user)):
    _teacher(user)
    return {"courses": STORE.courses(user.tenant_id)}


@app.get("/v1/teacher/open-items")
def teacher_open_items(user: User = Depends(current_user)):
    _teacher(user)
    return {"items": [{"id": item.id, "stem": item.stem, "stimulus": item.stimulus,
                       "competencies": [{**entry, "rubric": rubric_snapshot(entry["id"])}
                                       for entry in competencies_for_item(item.id)]}
                      for item in BANK.items.values() if item.kind == "open"]}


@app.post("/v1/teacher/open-assignments")
def teacher_create_open_assignment(body: OpenAssignmentIn, user: User = Depends(current_user)):
    _teacher(user)
    item = BANK.items.get(body.item_id)
    if not item or item.kind != "open":
        raise HTTPException(400, "El ejercicio seleccionado no es una pregunta abierta válida.")
    title = body.title.strip()
    instructions = body.instructions.strip()
    if not title or len(title) > 160 or len(instructions) > 4000:
        raise HTTPException(400, "Título obligatorio (máximo 160 caracteres) e instrucciones de hasta 4000 caracteres.")
    if body.course_id and not any(c["course_id"] == body.course_id for c in STORE.courses(user.tenant_id)):
        raise HTTPException(404, "curso no encontrado en esta escuela")
    due_at = None
    if body.due_at:
        try:
            parsed_due = datetime.fromisoformat(body.due_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(400, "La fecha límite debe ser una fecha ISO 8601 válida con zona horaria.") from exc
        if parsed_due.tzinfo is None:
            raise HTTPException(400, "La fecha límite debe incluir zona horaria.")
        parsed_due = parsed_due.astimezone(timezone.utc)
        if parsed_due <= datetime.now(timezone.utc):
            raise HTTPException(400, "La fecha límite debe estar en el futuro.")
        due_at = parsed_due.isoformat()
    competency_id = body.competency_id
    if competency_id and not valid_competency_for_item(item.id, competency_id):
        raise HTTPException(400, "La competencia seleccionada no está vinculada a esta plantilla del banco.")
    snapshot = rubric_snapshot(competency_id) if competency_id else None
    assignment_id = str(uuid.uuid4())
    STORE.create_open_assignment(assignment_id, user.tenant_id, body.course_id, item.id, title,
                                 instructions, _pid(user), due_at, competency_id, snapshot)
    STORE.audit(user.tenant_id, _pid(user), "actividad_abierta_creada", assignment_id)
    return {"id": assignment_id, "status": "created"}


@app.get("/v1/teacher/open-assignments")
def teacher_open_assignments(course: str | None = None, user: User = Depends(current_user)):
    _teacher(user)
    return {"assignments": STORE.open_assignments_for_teacher(user.tenant_id, course)}


@app.get("/v1/teacher/open-assignments/{assignment_id}/submissions")
def teacher_open_submissions(assignment_id: str, user: User = Depends(current_user)):
    _teacher(user)
    assignments = {a["id"] for a in STORE.open_assignments_for_teacher(user.tenant_id)}
    if assignment_id not in assignments:
        raise HTTPException(404, "actividad no encontrada")
    submissions = STORE.open_submissions_for_assignment(user.tenant_id, assignment_id)
    names = _nrps_names(user) if submissions else {}
    for submission in submissions:
        student_key = submission.pop("student_key", None)
        student_name = names.get(student_key)
        if student_name:
            submission["student_name"] = student_name
    return {"submissions": submissions}


@app.get("/v1/teacher/open-submissions/{submission_id}/history")
def teacher_open_submission_history(submission_id: str, user: User = Depends(current_user)):
    _teacher(user)
    attempts = STORE.open_submission_history_for_teacher(user.tenant_id, submission_id)
    if not attempts:
        raise HTTPException(404, "entrega no encontrada")
    names = _nrps_names(user)
    for attempt in attempts:
        student_key = attempt.pop("student_key", None)
        student_name = names.get(student_key)
        if student_name:
            attempt["student_name"] = student_name
    return {"attempts": attempts}


@app.post("/v1/teacher/open-submissions/{submission_id}/grade")
def teacher_grade_open_submission(submission_id: str, body: OpenGradeIn, user: User = Depends(current_user)):
    _teacher(user)
    if not 0 <= body.score <= 100 or len(body.feedback) > 10000:
        raise HTTPException(400, "La calificación debe estar entre 0 y 100 y la devolución no superar 10000 caracteres.")
    snapshot = STORE.rubric_snapshot_for_submission(user.tenant_id, submission_id)
    if snapshot:
        expected = {criterion["id"] for criterion in snapshot["criteria"]}
        if set(body.rubric) != expected:
            raise HTTPException(400, "La corrección debe puntuar todos los criterios de la rúbrica asignada.")
        if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 4
               for v in body.rubric.values()):
            raise HTTPException(400, "Cada criterio debe recibir una puntuación entera entre 0 y 4.")
    elif len(body.rubric) > 20 or any(
        not isinstance(k, str) or len(k) > 80 or isinstance(v, bool) or
        not isinstance(v, (int, float)) or not 0 <= v <= 4
        for k, v in body.rubric.items()
    ):
        raise HTTPException(400, "Cada criterio de la rúbrica debe tener una puntuación numérica entre 0 y 4.")
    if not STORE.grade_open_submission(user.tenant_id, submission_id, _pid(user), body.score,
                                       body.feedback.strip(), body.rubric):
        raise HTTPException(409, "La entrega no existe o ya fue corregida.")
    STORE.audit(user.tenant_id, _pid(user), "respuesta_abierta_corregida", submission_id)
    return {"status": "corregida"}


@app.get("/v1/teacher/cohort")
def cohort(course: str | None = None, user: User = Depends(current_user)):
    """Distribución de niveles de la escuela (o de un curso): solo agregados, sin identificadores de estudiantes."""
    _teacher(user)
    results = STORE.finished_results(user.tenant_id, course)
    levels = Counter(r["level"] for r in results)
    return {"levels": {str(k): levels.get(k, 0) for k in range(1, 9)}, "n": len(results),
            "baseline_level": BASELINE_LEVEL, "ladder": LADDER}


def _monthly(results: list[dict], min_n: int = 1) -> list[dict]:
    by: dict[str, list[int]] = defaultdict(list)
    for r in results:
        by[r["at"].strftime("%Y-%m")].append(r["level"])
    out = []
    for period in sorted(by):
        lv = by[period]
        n = len(lv)
        if n < min_n:
            out.append({"period": period, "n": None, "suppressed": True, "mean_level": None, "share_baseline": None, "se": None})
            continue
        mean = sum(lv) / n
        se = (sum((x - mean) ** 2 for x in lv) / (n - 1) / n) ** 0.5 if n > 1 else None
        out.append({"period": period, "n": n, "suppressed": False, "mean_level": round(mean, 2),
                    "share_baseline": round(100 * sum(1 for x in lv if x >= BASELINE_LEVEL) / n, 1),
                    "se": None if se is None else round(se, 2)})
    return out


@app.get("/v1/teacher/trends")
def trends(course: str | None = None, user: User = Depends(current_user)):
    """Evolución mensual del nivel promedio y del porcentaje que alcanza el nivel mínimo propuesto (agregados)."""
    _teacher(user)
    return {"periods": _monthly(STORE.finished_dated(user.tenant_id, course)), "baseline_level": BASELINE_LEVEL,
            "note": "Los niveles son provisorios; compará períodos con cuidado cuando haya pocos estudiantes."}


@app.get("/v1/teacher/errors")
def errors(course: str | None = None, user: User = Depends(current_user)):
    _teacher(user)
    return {"errors": STORE.error_counts(user.tenant_id, course)}


def _class_skills(tenant: str, course: str | None) -> list[dict]:
    by_pid = defaultdict(list)
    for r in STORE.tenant_rows(tenant, course):
        by_pid[r["pid"]].append((r["item_id"], r["score"], r["answered_at"], r["hints"]))
    acc = defaultdict(list)
    for rows in by_pid.values():
        for sk, st in compute_mastery(rows).items():
            acc[sk].append(st.p)
    out = [{"skill": sk, "name": SKILLS[sk][0], "mean_p": round(sum(v) / len(v), 2), "students": len(v)} for sk, v in acc.items()]
    return sorted(out, key=lambda x: x["mean_p"])


@app.get("/v1/teacher/skills")
def class_skills(course: str | None = None, user: User = Depends(current_user)):
    _teacher(user)
    return {"skills": _class_skills(user.tenant_id, course)}


@app.get("/v1/teacher/item-analysis")
def item_analysis(user: User = Depends(current_user)):
    _teacher(user)
    return {"templates": family_stats(STORE.tenant_rows(user.tenant_id), BANK.items)}


@app.get("/v1/teacher/export.csv")
def export_csv(course: str | None = None, user: User = Depends(current_user)):
    _teacher(user)
    buf = io.StringIO()
    w = csv.writer(buf)
    results = STORE.finished_results(user.tenant_id, course)
    lv = Counter(r["level"] for r in results)
    w.writerow(["seccion", "clave", "valor", "detalle"])
    for k in range(1, 9):
        w.writerow(["nivel", f"N{k}", lv.get(k, 0), DESCRIPTORS[k]])
    for x in _class_skills(user.tenant_id, course):
        w.writerow(["habilidad", x["name"], x["mean_p"], f"{x['students']} estudiantes"])
    for tag, n in STORE.error_counts(user.tenant_id, course).items():
        w.writerow(["error_frecuente", tag, n, ""])
    STORE.audit(user.tenant_id, user.sub, "exportacion_csv", course or "")
    return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="resumen.csv"'})


@app.get("/v1/teacher/consent")
def consent_status(user: User = Depends(current_user)):
    _teacher(user)
    s = STORE.tenant_settings(user.tenant_id)
    return {"attested": bool(s["consent_attested_at"]), "at": s["consent_attested_at"], "by": s["consent_attested_by"], "required": REQUIRE_CONSENT}


@app.post("/v1/teacher/consent")
def consent_attest(user: User = Depends(current_user)):
    """La escuela declara que obtuvo el consentimiento de las familias (la responsabilidad es de la institución)."""
    _teacher(user)
    STORE.attest_consent(user.tenant_id, user.sub)
    STORE.audit(user.tenant_id, user.sub, "consentimiento_confirmado", "")
    return consent_status(user)


@app.get("/v1/admin/audit")
def audit(user: User = Depends(current_user)):
    _teacher(user)
    return {"events": STORE.audit_list(user.tenant_id)}


@app.get("/v1/review/templates")
def review_templates(user: User = Depends(current_user)):
    _curator(user)
    apply_reviews(BANK, STORE)
    out = []
    for tid, spec in TPL.SPEC.items():
        revs = STORE.reviews(scope_of(tid))
        items = [i for i in BANK.items.values() if i.template == tid]
        out.append({"id": tid, "title": spec[5], "level": spec[4], "axis": spec[1].value, "process": spec[2].value,
                    "n_items": len(items),
                    "n_approved": sum(1 for i in items if i.status in (Status.REVISADO, Status.PILOTO, Status.CALIBRADO, Status.OPERATIVO)),
                    **template_status(revs), "reviewed_by_me": any(r["reviewer"] == user.sub for r in revs)})
    return {"templates": out, "required_approvals": REQUIRED}


@app.get("/v1/review/templates/{tid}/sample")
def review_sample(tid: str, n: int = 5, user: User = Depends(current_user)):
    _curator(user)
    if tid not in TPL.SPEC:
        raise HTTPException(404, "plantilla no encontrada")
    items = sorted((i for i in BANK.items.values() if i.template == tid), key=lambda i: int(i.id.split("-")[1]))[: max(1, min(n, 10))]
    return {"template": tid, "title": TPL.SPEC[tid][5], "checklist": CHECKLIST,
            "items": [{"id": i.id, "stem": i.stem, "kind": i.kind, "stimulus": i.stimulus, "correct": i.correct,
                       "answer_text": i.params.get("answer_text"), "target_level": i.target_level, "license": i.license,
                       "explanation": explain(i)["steps"],
                       "options": [{"id": o.id, "text": o.text, "tag": o.tag} for o in i.options]} for i in items]}


@app.post("/v1/review/templates/{tid}")
def review_submit(tid: str, body: ReviewIn, user: User = Depends(current_user)):
    _curator(user)
    if tid not in TPL.SPEC:
        raise HTTPException(404, "plantilla no encontrada")
    if body.decision not in ("aprobar", "rechazar"):
        raise HTTPException(400, "la decisión debe ser aprobar o rechazar")
    if body.decision == "aprobar" and not all(body.checklist.get(k) is True for k in CHECKLIST):
        raise HTTPException(400, "para aprobar hay que tildar toda la lista de control")
    if body.decision == "rechazar" and len(body.comment.strip()) < 10:
        raise HTTPException(400, "para rechazar, explicá el motivo (al menos 10 caracteres)")
    if not STORE.add_review(scope_of(tid), user.sub, body.decision, body.comment.strip(), body.checklist):
        raise HTTPException(409, "ya revisaste esta plantilla")
    STORE.audit(user.tenant_id, user.sub, f"revision_{body.decision}", tid)
    apply_reviews(BANK, STORE)
    return template_status(STORE.reviews(scope_of(tid)))


MIN_CELL = 10     # supresión de celdas pequeñas en vistas de red


def _network(user: User) -> None:
    if user.role not in ("network", "admin"):
        raise HTTPException(403, "solo la red o la jurisdicción")


@app.post("/v1/network/tenants")
def network_add(body: NetworkInviteIn, user: User = Depends(current_user)):
    """Invita a una escuela; sus resultados no se comparten hasta que la escuela acepta."""
    _network(user)
    tenant = body.tenant_id.strip()
    if not tenant or len(tenant) > 128:
        raise HTTPException(400, "identificador de escuela inválido")
    if tenant == user.tenant_id:
        raise HTTPException(400, "una red no puede invitarse a sí misma")
    STORE.add_network_tenant(user.tenant_id, tenant)
    STORE.audit(user.tenant_id, user.sub, "invitacion_escuela_enviada", tenant)
    return {"tenants": STORE.network_tenants(user.tenant_id),
            "pending_tenants": STORE.pending_network_tenants(user.tenant_id)}


@app.get("/v1/teacher/network-invites")
def network_invites(user: User = Depends(current_user)):
    """Redes que solicitaron compartir los resultados agregados de esta escuela."""
    _teacher(user)
    return {"invites": STORE.pending_invites(user.tenant_id)}


@app.post("/v1/teacher/network-invites/{network_id}/{decision}")
def network_invite_answer(network_id: str, decision: str, user: User = Depends(current_user)):
    _teacher(user)
    if decision not in ("accept", "decline"):
        raise HTTPException(400, "la decisión debe ser accept o decline")
    if not STORE.answer_invite(network_id, user.tenant_id, decision == "accept"):
        raise HTTPException(404, "invitación pendiente no encontrada")
    STORE.audit(user.tenant_id, user.sub, f"invitacion_red_{decision}", network_id)
    return {"invites": STORE.pending_invites(user.tenant_id)}


@app.get("/v1/teacher/network-memberships")
def network_memberships(user: User = Depends(current_user)):
    _teacher(user)
    return {"networks": STORE.network_memberships(user.tenant_id)}


@app.delete("/v1/teacher/network-memberships/{network_id}")
def network_leave(network_id: str, user: User = Depends(current_user)):
    _teacher(user)
    if not STORE.leave_network(network_id, user.tenant_id):
        raise HTTPException(404, "la escuela no tiene una membresía aceptada en esa red")
    STORE.audit(user.tenant_id, user.sub, "consentimiento_red_retirado", network_id)
    return {"networks": STORE.network_memberships(user.tenant_id)}


@app.get("/v1/network/summary")
def network_summary(user: User = Depends(current_user)):
    """Resumen por escuela con supresión de celdas pequeñas: las escuelas con menos de 10 estudiantes se agrupan en
    «otras escuelas» y ese grupo solo se muestra si reúne al menos 10, para que no se deduzcan datos por diferencia."""
    _network(user)
    visible, hidden = [], []
    for t in STORE.network_tenants(user.tenant_id):
        lv = [r["level"] for r in STORE.finished_results(t)]
        (visible if len(lv) >= MIN_CELL else hidden).append((t, lv))

    def agg(lv):
        return {"n": len(lv), "mean_level": round(sum(lv) / len(lv), 2),
                "share_baseline": round(100 * sum(1 for x in lv if x >= BASELINE_LEVEL) / len(lv), 1)}
    schools = [{"school": t, **agg(lv)} for t, lv in visible]
    other = [x for _, lv in hidden for x in lv]
    shown = [x for _, lv in visible for x in lv]
    others_row = None
    if len(other) >= MIN_CELL:
        others_row = {"school": "Otras escuelas", **agg(other)}
        shown += other
    pending = STORE.pending_network_tenants(user.tenant_id)
    return {"network_id": user.tenant_id, "min_cell": MIN_CELL, "schools": schools, "others": others_row,
            "total": agg(shown) if shown else None, "baseline_level": BASELINE_LEVEL,
            "pending_invitations": len(pending), "pending_tenants": pending,
            "note": "Se muestran solo grupos de al menos 10 estudiantes y escuelas que aceptaron compartir sus agregados. Los niveles son provisorios."}


# ---- observatorio de resultados históricos --------------------------------------------
def _domain(domain: str) -> str:
    if domain not in DOMAINS:
        raise HTTPException(400, "dominio inválido")
    return domain


@app.get("/v1/observatory/meta")
def obs_meta(user: User = Depends(current_user)):
    return {"domains": DOMAINS, "cycles": sorted({o.cycle for o in OBS}), "entities": OA.entities(OBS), "reference": AVG_NAME,
            "has_se": any(o.se is not None for o in OBS), "has_gaps": bool(GAPS),
            "points_per_year": OA.POINTS_PER_YEAR,
            "notes": ["Solo agregados públicos con su fuente. Los datos marcados como secundarios deben contrastarse con las tablas oficiales.",
                      "Estas tablas no traen errores estándar: no se declara significancia estadística.",
                      "Argentina pasó de prueba en papel a computadora en 2022 y no tiene dato nacional de 2015."]}


@app.get("/v1/observatory/series")
def obs_series(domain: str = "matematica", entities: str | None = None, user: User = Depends(current_user)):
    _domain(domain)
    chosen = [e for e in (entities.split(",") if entities else ["Argentina", AVG_NAME]) if e][:12]
    groups = {x["entity"]: x["group"] for x in OA.entities(OBS, domain)}
    out = [{"entity": e, "group": groups[e], "points": [[c, v] for c, v in OA.series(OBS, e, domain)],
            "se": [[c, se] for c, se in OA.series_se(OBS, e, domain)],
            "changes": OA.significant_changes(OBS, e, domain),
            "trend": OA.trend_stats(OA.series(OBS, e, domain))} for e in chosen if e in groups]
    return {"domain": domain, "series": out, "region_average": [[c, v] for c, v in OA.region_average(OBS, domain)],
            "provenance": OA.provenance(OBS, domain, chosen)}


@app.get("/v1/observatory/compare")
def obs_compare(domain: str = "matematica", cycle: int = 2022, user: User = Depends(current_user)):
    _domain(domain)
    return {"domain": domain, "cycle": cycle, "rows": OA.compare(OBS, domain, cycle)}


@app.get("/v1/observatory/gaps")
def obs_gaps(entity: str = "Argentina", domain: str = "matematica", user: User = Depends(current_user)):
    """Brechas por género y nivel socioeconómico calculadas con microdatos (vacío hasta que se carguen)."""
    _domain(domain)
    rows = OA.gaps_for(GAPS, entity, domain)
    return {"entity": entity, "domain": domain, "has_data": bool(rows), "rows": rows}


@app.get("/v1/observatory/focus")
def obs_focus(entity: str = "Argentina", user: User = Depends(current_user)):
    return OA.focus(OBS, entity)


@app.get("/metrics")
def metrics():
    return Response(content="".join(f"matheval_{k} {v}\n" for k, v in sorted(METRICS.items())), media_type="text/plain; version=0.0.4")


@app.get("/healthz")
def health():
    return {"ok": True, "items": len(BANK.items), "approved": len(BANK.pool("practica")), "templates": len(TPL.SPEC)}


@app.get("/readyz")
def readiness():
    """Readiness probe: la instancia solo recibe tráfico si puede acceder a su base."""
    try:
        STORE.ping()
    except Exception:  # noqa: BLE001
        log.exception("falló la comprobación de disponibilidad de la base de datos")
        return JSONResponse({"ok": False, "dependency": "database"}, status_code=503)
    return {"ok": True, "database": "ok"}

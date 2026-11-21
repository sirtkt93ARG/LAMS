"""Prueba la lógica de los endpoints llamando a las funciones directamente. Si FastAPI no está instalado
(p. ej. sin red), se usa un sustituto mínimo; con FastAPI real también corre."""
import os, sys, time, types, unittest
import tempfile
_TMP = tempfile.mkdtemp()
os.environ.update({"MATHEVAL_DEV": "1", "BANK_PATH": "data/bank_demo.jsonl", "DATABASE_URL": f"sqlite:///{_TMP}/api.db", "SESSION_SECRET": "s" * 40,
                   "LTI_HANDOFF_SECRET": "h" * 40})
sys.path.insert(0, os.getcwd())
import jwt

try:
    import fastapi, pydantic  # noqa: F401
except ImportError:
    fa = types.ModuleType("fastapi")
    class HTTPException(Exception):
        def __init__(self, status_code, detail=None):
            self.status_code, self.detail = status_code, detail
    class FastAPI:
        def __init__(self, **kw): pass
        def add_middleware(self, *a, **k): pass
        def _route(self, *a, **k): return lambda f: f
        get = post = delete = middleware = _route
    class BackgroundTasks:
        def __init__(self): self.tasks = []
        def add_task(self, f, *a): self.tasks.append((f, a))
    fa.HTTPException, fa.FastAPI, fa.BackgroundTasks = HTTPException, FastAPI, BackgroundTasks
    class Response:
        def __init__(self, content="", media_type=None, headers=None):
            self.body, self.media_type, self.headers = content.encode() if isinstance(content, str) else content, media_type, headers or {}
    fr = types.ModuleType("fastapi.responses"); fr.Response = Response
    sys.modules["fastapi.responses"] = fr
    fa.Depends = lambda x: x
    fa.Header = lambda default=None: default
    mw = types.ModuleType("fastapi.middleware"); cors = types.ModuleType("fastapi.middleware.cors")
    cors.CORSMiddleware = object
    pd = types.ModuleType("pydantic")
    class BaseModel:
        def __init__(self, **kw):
            for k, v in kw.items(): setattr(self, k, v)
    pd.BaseModel = BaseModel
    sys.modules.update({"fastapi": fa, "fastapi.middleware": mw, "fastapi.middleware.cors": cors, "pydantic": pd})

from fastapi import BackgroundTasks, HTTPException
from api.app import main as M
from api.app.auth import User, current_user


class TestApiLogic(unittest.TestCase):
    def run_session(self, user, correct=True):
        out = M.start(M.StartIn(mode="practica"), user)
        sid = out["session_id"]
        self.assertEqual(out["total"], 24)
        while not out["done"]:
            item = M.BANK.items[out["items"][0]["id"]]
            resp = item.correct if item.kind == "choice" else str(item.correct)
            if not correct:
                resp = "zzz"
            out = M.answer(sid, M.AnswerIn(item_id=item.id, response=str(resp), duration_s=5.0), BackgroundTasks(), user)
            self.assertEqual(out["correct"], correct)
        return sid

    def test_full_flow_and_report(self):
        u = User("alumno-1", "escuela-1", "student")
        sid = self.run_session(u, True)
        rep = M.report(sid, u)
        self.assertEqual(rep["answered"], 24)
        self.assertEqual(len(rep["ladder"]), 8)
        self.assertGreaterEqual(rep["level"], 5)
        sid2 = self.run_session(User("alumno-2", "escuela-1", "student"), False)
        rep2 = M.report(sid2, User("alumno-2", "escuela-1", "student"))
        self.assertLessEqual(rep2["level"], 2)
        self.assertTrue(rep2["error_tags"])

    def test_student_view_hides_answers(self):
        out = M.start(M.StartIn(), User("a", "t", "student"))
        blob = str(out)
        for forbidden in ("correct", "tag", "params", "answer"):
            self.assertNotIn(f"'{forbidden}'", blob)

    def test_isolation_and_permissions(self):
        a = User("a1", "t1", "student")
        sid = M.start(M.StartIn(), a)["session_id"]
        for other in (User("b1", "t1", "student"), User("a1", "t2", "student")):
            with self.assertRaises(HTTPException) as c:
                M.pending(sid, other)
            self.assertEqual(c.exception.status_code, 404)
        with self.assertRaises(HTTPException) as c:
            M.start(M.StartIn(), User("t", "t1", "teacher"))
        self.assertEqual(c.exception.status_code, 403)
        with self.assertRaises(HTTPException) as c:
            M.cohort(None, a)
        self.assertEqual(c.exception.status_code, 403)
        with self.assertRaises(HTTPException) as c:
            M.answer(sid, M.AnswerIn(item_id="no-pendiente"), BackgroundTasks(), a)
        self.assertEqual(c.exception.status_code, 409)
        with self.assertRaises(HTTPException) as c:
            M.start(M.StartIn(mode="otro"), a)
        self.assertEqual(c.exception.status_code, 400)

    def test_sessions_survive_restart_and_store_only_pseudonym(self):
        u = User("alumno-persist", "escuela-p", "student")
        out = M.start(M.StartIn(), u)
        sid = out["session_id"]
        item = M.BANK.items[out["items"][0]["id"]]
        M.answer(sid, M.AnswerIn(item_id=item.id, response=str(item.correct)), BackgroundTasks(), u)
        row = M.STORE.load_session(sid, "escuela-p")          # lo que quedó en la base
        self.assertNotIn("alumno-persist", str(row))
        self.assertNotEqual(row["pid"], "alumno-persist")
        again = M.pending(sid, u)                              # reconstruye desde la base
        self.assertEqual(again["answered"], 1)
        self.assertEqual(M.report(sid, u)["answered"], 1)

    def test_teacher_can_read_report_in_tenant_but_students_cannot_cross(self):
        u = User("alumno-x", "escuela-q", "student")
        sid = M.start(M.StartIn(), u)["session_id"]
        self.assertEqual(M.report(sid, User("doc", "escuela-q", "teacher"))["answered"], 0)
        with self.assertRaises(HTTPException):
            M.report(sid, User("otro", "escuela-q", "student"))

    def test_review_endpoints(self):
        doc = User("docente-9", "escuela-r", "teacher")
        listing = M.review_templates(doc)
        self.assertEqual(len(listing["templates"]), 24)
        sample = M.review_sample("T1", 5, doc)
        self.assertEqual(len(sample["items"]), 5)
        self.assertIn("correct", sample["items"][0])
        with self.assertRaises(HTTPException) as c:
            M.review_templates(User("a", "t", "student"))
        self.assertEqual(c.exception.status_code, 403)
        with self.assertRaises(HTTPException) as c:               # lista de control incompleta
            M.review_submit("T9", M.ReviewIn(decision="aprobar", checklist={"clave_correcta": True}), doc)
        self.assertEqual(c.exception.status_code, 400)
        with self.assertRaises(HTTPException) as c:               # rechazar sin motivo
            M.review_submit("T9", M.ReviewIn(decision="rechazar", comment="no"), doc)
        self.assertEqual(c.exception.status_code, 400)
        full = {k: True for k in M.CHECKLIST}
        out = M.review_submit("T9", M.ReviewIn(decision="aprobar", checklist=full), doc)
        self.assertEqual(out["status"], "aprobada")
        self.assertTrue(all(i.status.value == "revisado" for i in M.BANK.items.values() if i.template == "T9"))
        with self.assertRaises(HTTPException) as c:
            M.review_submit("T9", M.ReviewIn(decision="aprobar", checklist=full), doc)
        self.assertEqual(c.exception.status_code, 409)
        out = M.review_submit("T8", M.ReviewIn(decision="rechazar", comment="La tabla es confusa para el grupo"),
                              User("docente-10", "escuela-r", "teacher"))
        self.assertEqual(out["status"], "rechazada")
        self.assertTrue(all(i.status.value == "rechazado" for i in M.BANK.items.values() if i.template == "T8"))

    def test_directed_practice_hints_explanations_and_mastery(self):
        u = User("alumno-d1", "escuela-d", "student")
        out = M.start(M.StartIn(mode="dirigida", skill="porcentajes"), u)
        sid = out["session_id"]
        self.assertEqual(out["total"], 10)
        item = M.BANK.items[out["items"][0]["id"]]
        self.assertIn("porcentajes", __import__("matheval.skills", fromlist=["x"]).skills_of_item(item.id))
        h = M.hint(sid, item.id, 1, u)
        self.assertTrue(h["hint"])
        with self.assertRaises(HTTPException) as c:
            M.hint(sid, "otro-item", 1, u)
        self.assertEqual(c.exception.status_code, 409)
        r = M.answer(sid, M.AnswerIn(item_id=item.id, response="zzz"), BackgroundTasks(), u)       # error -> espejo
        self.assertFalse(r["correct"])
        self.assertEqual(r["explanation"][-1], f"Respuesta: {item.params['answer_text']}")
        self.assertEqual(r["items"][0]["id"].split("-")[0], item.template)
        again = M.answer(sid, M.AnswerIn(item_id=item.id, response="zzz"), BackgroundTasks(), u)    # reintento idempotente
        self.assertTrue(again["duplicate"] and not again["correct"])
        self.assertEqual(again["answered"], 1)
        while not r["done"]:
            nxt = M.BANK.items[r["items"][0]["id"]]
            r = M.answer(sid, M.AnswerIn(item_id=nxt.id, response=str(nxt.correct)), BackgroundTasks(), u)
        rep = M.report(sid, u)
        self.assertEqual((rep["kind"], rep["skill"]), ("dirigida", "porcentajes"))
        self.assertEqual(len(rep["mistakes"]), 1)
        prog = M.progress(u)
        self.assertEqual(prog["responses"], 10)
        self.assertTrue(any(m["skill"] == "porcentajes" and m["p_known"] for m in prog["mastery"]))
        self.assertEqual(M.hint.__name__, "hint")
        with self.assertRaises(HTTPException) as c:
            M.start(M.StartIn(mode="dirigida", skill="inventada"), u)
        self.assertEqual(c.exception.status_code, 400)
        # con ayuda no cuenta como evidencia de dominio: la fila quedó con hints=1
        self.assertEqual(M.STORE.tenant_rows("escuela-d")[0]["hints"], 1)

    def test_pilot_mode_collects_one_item_per_template(self):
        u = User("alumno-p1", "escuela-pi", "student")
        out = M.start(M.StartIn(mode="piloto"), u)
        sid, seen = out["session_id"], set()
        self.assertEqual(out["total"], 24)
        while not out["done"]:
            it = M.BANK.items[out["items"][0]["id"]]
            seen.add(it.template)
            out = M.answer(sid, M.AnswerIn(item_id=it.id, response=str(it.correct)), BackgroundTasks(), u)
            self.assertNotIn("correct", out)              # el piloto no devuelve corrección
        self.assertEqual(len(seen), 24)
        self.assertEqual(M.report(sid, u)["kind"], "piloto")

    def test_consent_gate_and_deletion_and_audit(self):
        old = M.REQUIRE_CONSENT
        M.REQUIRE_CONSENT = True
        try:
            st, teacher = User("al-c", "escuela-c", "student"), User("doc-c", "escuela-c", "teacher")
            with self.assertRaises(HTTPException) as c:
                M.start(M.StartIn(), st)
            self.assertEqual(c.exception.status_code, 403)
            self.assertFalse(M.consent_status(teacher)["attested"])
            self.assertTrue(M.consent_attest(teacher)["attested"])
            sid = M.start(M.StartIn(), st)["session_id"]
            item = M.BANK.items[M.pending(sid, st)["items"][0]["id"]]
            M.answer(sid, M.AnswerIn(item_id=item.id, response=str(item.correct)), BackgroundTasks(), st)
            self.assertEqual(M.delete_my_data(st), {"sessions": 1, "responses": 1})
            with self.assertRaises(HTTPException):
                M.pending(sid, st)
            actions = [e["action"] for e in M.audit(teacher)["events"]]
            self.assertIn("consentimiento_confirmado", actions)
            self.assertIn("supresion_de_datos", actions)
        finally:
            M.REQUIRE_CONSENT = old

    def test_rate_limit_and_metrics(self):
        u = User("al-r", "escuela-rl", "student")
        sid = M.start(M.StartIn(), u)["session_id"]
        item_id = M.pending(sid, u)["items"][0]["id"]
        from api.app.limits import RateLimiter
        old = M.LIM
        M.LIM = RateLimiter()
        try:
            codes = []
            for _ in range(250):
                try:
                    M.answer(sid, M.AnswerIn(item_id="no-existe"), BackgroundTasks(), u)
                except HTTPException as e:
                    codes.append(e.status_code)
            self.assertEqual(codes.count(409), 240)
            self.assertEqual(codes.count(429), 10)
        finally:
            M.LIM = old
        self.assertIn("matheval_", M.metrics().body.decode() or "matheval_")

    def test_grade_passback_payload(self):
        sent = {}
        class Resp: status = 200
        def fake(req, timeout=0):
            sent.update(url=req.full_url, body=__import__("json").loads(req.data), secret=req.get_header("X-internal-secret"))
            return Resp()
        old_u, old_url = M.urllib.request.urlopen, M.LTI_SERVICE_URL
        M.urllib.request.urlopen, M.LTI_SERVICE_URL = fake, "http://lti.test"
        try:
            ags = {"iss": "http://lms", "client_id": "cli", "lineitem": "http://lms/lineitems/1"}
            M._send_grade(User("u-ags", "dep", "student", "c1", "4.º A", ags), {"level": 6}, "practica")
            self.assertEqual(sent["url"], "http://lti.test/lti/ags/score")
            self.assertEqual((sent["body"]["user_id"], sent["body"]["score_given"], sent["body"]["score_maximum"]), ("u-ags", 6, 8))
            self.assertIn("preliminar", sent["body"]["comment"])
            sent.clear()
            M._send_grade(User("u2", "dep", "student"), {"level": 3}, "practica")      # sin datos de notas: no hace nada
            self.assertEqual(sent, {})
        finally:
            M.urllib.request.urlopen, M.LTI_SERVICE_URL = old_u, old_url

    def test_teacher_analytics_by_course_and_csv(self):
        for k, course in enumerate(["4A", "4A", "4B"]):
            u = User(f"al-t{k}", "escuela-t", "student", course, f"Curso {course}")
            self.run_session(u, k != 1)
        doc = User("doc-t", "escuela-t", "teacher")
        self.assertEqual([c["course_id"] for c in M.courses(doc)["courses"]], ["4A", "4B"])
        self.assertEqual(M.cohort("4A", doc)["n"], 2)
        self.assertEqual(M.cohort("4B", doc)["n"], 1)
        self.assertEqual(M.cohort(None, doc)["n"], 3)
        self.assertTrue(M.errors("4A", doc)["errors"])
        skills = M.class_skills(None, doc)["skills"]
        self.assertTrue(skills and skills == sorted(skills, key=lambda x: x["mean_p"]))
        ia = M.item_analysis(doc)["templates"]
        self.assertTrue(ia and all("p" in t for t in ia))
        csv_text = M.export_csv("4A", doc).body.decode()
        self.assertTrue(csv_text.startswith("seccion,clave,valor,detalle"))
        self.assertIn("N8", csv_text)
        self.assertIn("exportacion_csv", [e["action"] for e in M.audit(doc)["events"]])
        with self.assertRaises(HTTPException):
            M.export_csv(None, User("a", "escuela-t", "student"))

    def test_trends_by_month_and_network_suppression(self):
        from datetime import datetime, timezone
        doc = User("doc-n", "escuela-n1", "teacher")
        for k in range(3):
            self.run_session(User(f"al-n{k}", "escuela-n1", "student"), k != 0)
        tr = M.trends(None, doc)
        self.assertEqual(len(tr["periods"]), 1)
        p0 = tr["periods"][0]
        self.assertEqual((p0["n"], p0["suppressed"]), (3, False))
        self.assertTrue(1 <= p0["mean_level"] <= 8 and 0 <= p0["share_baseline"] <= 100 and p0["se"] is not None)
        self.assertEqual(M._monthly([{"at": datetime(2026, 11, 3, tzinfo=timezone.utc), "level": 4}], min_n=10)[0]["suppressed"], True)
        def fill(net, tenant, n):
            M.network_add(M.ExchangeIn(token=tenant), net)
            for k in range(n):
                u = User(f"x-{tenant}-{k}", tenant, "student")
                sid = M.start(M.StartIn(), u)["session_id"]
                M.STORE.save_session(sid, tenant, M._state_of(M._load(sid, u)), {"theta": 0.0, "se": 0.3, "level": 4, "kind": "mst"})
        net = User("red-1", "red-1", "network")
        M.network_add(M.ExchangeIn(token="escuela-n1"), net)
        M.network_add(M.ExchangeIn(token="escuela-n1"), net)                    # idempotente
        self.assertEqual(M.STORE.network_tenants("red-1"), ["escuela-n1"])
        fill(net, "escuela-n2", 12); fill(net, "escuela-n3", 4); fill(net, "escuela-n4", 3)
        out = M.network_summary(net)
        self.assertEqual([x["school"] for x in out["schools"]], ["escuela-n2"])      # solo la que tiene 10 o más
        self.assertEqual((out["others"]["school"], out["others"]["n"]), ("Otras escuelas", 10))   # 3 + 4 + 3 se agrupan
        self.assertEqual(out["total"]["n"], 22)
        net2 = User("red-2", "red-2", "network")
        fill(net2, "escuela-b1", 12); fill(net2, "escuela-b2", 3)
        out2 = M.network_summary(net2)
        self.assertIsNone(out2["others"])                                             # menos de 10 agrupados: no se muestran
        self.assertEqual(out2["total"]["n"], 12)                                      # y no entran en el total
        self.assertNotIn("escuela-b2", str(out2))
        with self.assertRaises(HTTPException) as c:
            M.network_summary(User("doc", "escuela-n1", "teacher"))
        self.assertEqual(c.exception.status_code, 403)

    def test_observatory_endpoints(self):
        u = User("any", "t", "student")
        meta = M.obs_meta(u)
        self.assertIn("matematica", meta["domains"])
        self.assertTrue(any(e["entity"] == "Argentina" for e in meta["entities"]))
        ser = M.obs_series("matematica", "Argentina,Chile,Inventado", u)
        self.assertEqual([s["entity"] for s in ser["series"]], ["Argentina", "Chile"])
        self.assertEqual(ser["series"][0]["points"][-1], [2025, 367])
        self.assertTrue(ser["provenance"] and ser["region_average"])
        self.assertEqual(M.obs_compare("matematica", 2022, u)["rows"][0]["entity"], "Hong Kong (China)")
        self.assertEqual(M.obs_focus("Argentina", u)["domains"]["matematica"]["total_change"], -14)
        with self.assertRaises(HTTPException) as c:
            M.obs_series("historia", None, u)
        self.assertEqual(c.exception.status_code, 400)

    def test_observatory_standard_errors_and_gaps(self):
        from dataclasses import replace
        from matheval.observatory.data import GapRow
        u = User("any", "t", "student")
        self.assertFalse(M.obs_gaps("Argentina", "matematica", u)["has_data"])
        self.assertEqual(M.obs_series("matematica", "Argentina", u)["series"][0]["changes"], [])        # sin errores estándar no hay prueba
        old_obs, old_gaps = M.OBS, M.GAPS
        try:
            M.OBS = [replace(o, se=2.0) if (o.entity == "Argentina" and o.domain == "matematica") else o for o in old_obs]
            M.GAPS = [GapRow(2022, "matematica", "Argentina", "escs_cuartil", "Q1", 330.0, 3.1, 900, "calc", "microdatos_propios")]
            self.assertTrue(M.obs_meta(u)["has_se"] and M.obs_meta(u)["has_gaps"])
            s = M.obs_series("matematica", "Argentina", u)["series"][0]
            self.assertTrue(all(se == 2.0 for _, se in s["se"]))
            ch = {(c["from"], c["to"]): c for c in s["changes"]}
            self.assertTrue(ch[(2018, 2022)]["significant"] is False and ch[(2022, 2025)]["significant"] is True)   # -1 no, -11 sí
            g = M.obs_gaps("Argentina", "matematica", u)
            self.assertEqual((g["has_data"], g["rows"][0]["group"], g["rows"][0]["value"]), (True, "Q1", 330.0))
            self.assertEqual(M.obs_gaps("Chile", "matematica", u)["rows"], [])
        finally:
            M.OBS, M.GAPS = old_obs, old_gaps

    def test_cohort_is_aggregate_only(self):
        self.run_session(User("c1", "escuela-9", "student"), True)
        self.run_session(User("c2", "escuela-9", "student"), False)
        out = M.cohort(None, User("doc", "escuela-9", "teacher"))
        self.assertEqual(out["n"], 2)
        self.assertEqual(sum(out["levels"].values()), 2)
        self.assertNotIn("c1", str(out))
        self.assertEqual(M.cohort(None, User("doc", "escuela-vacia", "teacher"))["n"], 0)

    def test_lti_exchange_and_bearer(self):
        handoff = jwt.encode({"sub": "u-77", "tenant_id": "dep-1", "role": "student", "iss": "matheval-lti",
                              "aud": "matheval-api", "iat": int(time.time()), "jti": "api-logic-handoff-1",
                              "exp": int(time.time()) + 60}, "h" * 40, algorithm="HS256")
        out = M.lti_exchange(M.ExchangeIn(token=handoff))
        user = current_user(authorization="Bearer " + out["access_token"], x_dev_user=None)
        self.assertEqual((user.sub, user.tenant_id, user.role), ("u-77", "dep-1", "student"))
        bad = jwt.encode({"sub": "u", "tenant_id": "t", "role": "superusuario", "exp": int(time.time()) + 60}, "h" * 40, algorithm="HS256")
        with self.assertRaises(HTTPException):
            M.lti_exchange(M.ExchangeIn(token=bad))              # rol no permitido
        expired = jwt.encode({"sub": "u", "tenant_id": "t", "role": "student", "exp": int(time.time()) - 5}, "h" * 40, algorithm="HS256")
        with self.assertRaises(HTTPException):
            M.lti_exchange(M.ExchangeIn(token=expired))
        forged = jwt.encode({"sub": "u", "tenant_id": "t", "role": "teacher", "iss": "matheval-lti", "aud": "matheval-api",
                             "exp": int(time.time()) + 60}, "otra-clave" * 5, algorithm="HS256")
        with self.assertRaises(HTTPException):
            current_user(authorization="Bearer " + forged, x_dev_user=None)


if __name__ == "__main__":
    unittest.main()

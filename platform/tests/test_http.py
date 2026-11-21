"""Pruebas por HTTP con el TestClient de FastAPI (requiere fastapi y httpx reales; si no están, se omiten)."""
import os, sys, tempfile, time, unittest, io, json
from unittest.mock import patch
_TMP = tempfile.mkdtemp()
for k, v in {"MATHEVAL_DEV": "1", "BANK_PATH": "data/bank_demo.jsonl", "DATABASE_URL": f"sqlite:///{_TMP}/http.db",
             "SESSION_SECRET": "s" * 40, "LTI_HANDOFF_SECRET": "h" * 40}.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, os.getcwd())
import jwt

try:
    from fastapi.testclient import TestClient
    from api.app import main as M
    READY = True
except Exception:          # sin FastAPI/httpx reales (p. ej. con el sustituto de test_api_logic)
    READY = False

S = {"X-Dev-User": "alumno-h1:escuela-h:student"}
T = {"X-Dev-User": "docente-h1:escuela-h:teacher"}
A = {"X-Dev-User": "curador-h1:institucion:admin"}
N = {"X-Dev-User": "red-http:red-http:network"}


@unittest.skipUnless(READY, "FastAPI o httpx no disponibles")
class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(M.app)

    def test_readiness_checks_database_connectivity(self):
        ready = self.c.get("/readyz")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json(), {"ok": True, "database": "ok"})
        original = M.STORE.ping
        M.STORE.ping = lambda: (_ for _ in ()).throw(RuntimeError("database unavailable"))
        try:
            unavailable = self.c.get("/readyz")
            self.assertEqual(unavailable.status_code, 503)
            self.assertEqual(unavailable.json(), {"ok": False, "dependency": "database"})
            # Liveness stays healthy: a DB outage must not trigger restart loops.
            self.assertEqual(self.c.get("/healthz").status_code, 200)
        finally:
            M.STORE.ping = original

    def test_health_and_auth_required(self):
        r = self.c.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["items"], 3500)  # banco deduplicado por contenido
        self.assertEqual(self.c.post("/v1/sessions", json={"mode": "practica"}).status_code, 401)
        self.assertEqual(self.c.post("/v1/sessions", json={"mode": "practica"}, headers={"X-Dev-User": "mal"}).status_code, 400)

    def test_cors_preflight_for_web_origin(self):
        r = self.c.options("/v1/sessions", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
                                                    "Access-Control-Request-Headers": "content-type,x-dev-user,authorization"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["access-control-allow-origin"], "http://localhost:3000")

    def test_full_student_flow_and_teacher_views(self):
        r = self.c.post("/v1/sessions", json={"mode": "practica"}, headers=S)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        sid = body["session_id"]
        for forbidden in ('"tag"', '"params"', '"correct"'):
            self.assertNotIn(forbidden, r.text)
        self.assertEqual(self.c.post(f"/v1/sessions/{sid}/answers", json={}, headers=S).status_code, 422)
        while not body["done"]:
            item = M.BANK.items[body["items"][0]["id"]]
            r = self.c.post(f"/v1/sessions/{sid}/answers", json={"item_id": item.id, "response": str(item.correct)}, headers=S)
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertTrue(body["correct"])
        rep = self.c.get(f"/v1/sessions/{sid}/report", headers=S).json()
        self.assertEqual(rep["answered"], 24)
        self.assertGreaterEqual(rep["level"], 5)
        self.assertEqual(self.c.get(f"/v1/sessions/{sid}/report", headers={"X-Dev-User": "otro:escuela-h:student"}).status_code, 404)
        co = self.c.get("/v1/teacher/cohort", headers=T).json()
        self.assertGreaterEqual(co["n"], 1)
        self.assertEqual(self.c.get("/v1/teacher/cohort", headers=S).status_code, 403)

    def test_open_response_assignment_submission_and_teacher_grading(self):
        item = next((i for i in M.BANK.items.values() if i.kind == "open"), None)
        if item is None:
            self.skipTest("el banco de pruebas no contiene ítems abiertos")
        created = self.c.post("/v1/teacher/open-assignments", headers=T,
                              json={"item_id": item.id, "title": "Explicá tu estrategia", "instructions": "Justificá cada paso."})
        self.assertEqual(created.status_code, 200, created.text)
        assignment_id = created.json()["id"]
        self.assertEqual(self.c.get("/v1/student/open-assignments", headers=T).status_code, 403)
        assignments = self.c.get("/v1/student/open-assignments", headers=S)
        self.assertEqual(assignments.status_code, 200, assignments.text)
        self.assertTrue(any(a["id"] == assignment_id for a in assignments.json()["assignments"]))
        submitted = self.c.post(f"/v1/student/open-assignments/{assignment_id}/submit", headers=S,
                                json={"response": "Primero analicé los datos y luego justifiqué el resultado."})
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(self.c.post(f"/v1/student/open-assignments/{assignment_id}/submit", headers=S,
                                     json={"response": "duplicada"}).status_code, 409)
        submissions = self.c.get(f"/v1/teacher/open-assignments/{assignment_id}/submissions", headers=T)
        self.assertEqual(submissions.status_code, 200, submissions.text)
        submission_id = submissions.json()["submissions"][0]["id"]
        graded = self.c.post(f"/v1/teacher/open-submissions/{submission_id}/grade", headers=T,
                             json={"score": 82, "feedback": "Buen desarrollo.", "rubric": {"argumentacion": 4}})
        self.assertEqual(graded.status_code, 200, graded.text)
        result = self.c.get(f"/v1/student/open-submissions/{submission_id}", headers=S)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["score"], 82)
        self.assertEqual(self.c.get(f"/v1/student/open-submissions/{submission_id}",
                                    headers={"X-Dev-User": "otro:escuela-h:student"}).status_code, 404)

    def test_nrps_names_are_resolved_in_memory_without_persisting_roster(self):
        user = M.User(sub="docente-lms-1", tenant_id="escuela-h", role="teacher",
                      nrps={"iss": "https://lms.example", "client_id": "client-1",
                            "context_memberships_url": "https://lms.example/members"})
        payload = {"members": [
            {"user_id": "alumno-h1", "name": "Nombre Alumno", "email": "private@example.test"},
        ]}
        original_url = M.LTI_SERVICE_URL
        M.LTI_SERVICE_URL = "http://lti.internal"
        try:
            with patch("api.app.main.urllib.request.urlopen",
                       return_value=io.BytesIO(json.dumps(payload).encode())):
                names = M._nrps_names(user)
        finally:
            M.LTI_SERVICE_URL = original_url
        label = M._student_label("alumno-h1", "escuela-h")
        self.assertEqual(names, {label: "Nombre Alumno"})
        self.assertNotIn("private@example.test", str(names))

    def test_competency_rubric_is_snapshotted_and_enforced_over_http(self):
        from matheval.rubrics import competencies_for_item

        item = next((i for i in M.BANK.items.values()
                     if i.kind == "open" and competencies_for_item(i.id)), None)
        if item is None:
            self.skipTest("el banco de pruebas no tiene ítems abiertos vinculados a competencias")
        competency = competencies_for_item(item.id)[0]
        invalid = self.c.post("/v1/teacher/open-assignments", headers=T, json={
            "item_id": item.id, "title": "Competencia ajena", "competency_id": "competencia_inexistente",
        })
        self.assertEqual(invalid.status_code, 400, invalid.text)
        catalog = self.c.get("/v1/teacher/open-items", headers=T)
        self.assertEqual(catalog.status_code, 200, catalog.text)
        catalog_item = next(entry for entry in catalog.json()["items"] if entry["id"] == item.id)
        self.assertEqual(catalog_item["competencies"][0]["id"], competency["id"])
        self.assertEqual(set(catalog_item["competencies"][0]["rubric"]["criteria"][0]["descriptors"]),
                         {"0", "1", "2", "3", "4"})
        created = self.c.post("/v1/teacher/open-assignments", headers=T, json={
            "item_id": item.id, "title": "Rúbrica por competencia",
            "competency_id": competency["id"],
        })
        self.assertEqual(created.status_code, 200, created.text)
        assignment_id = created.json()["id"]
        assignment = next(a for a in self.c.get("/v1/student/open-assignments", headers=S).json()["assignments"]
                          if a["id"] == assignment_id)
        snapshot = assignment["rubric_snapshot"]
        self.assertEqual(snapshot["competency_id"], competency["id"])
        self.assertEqual(len(snapshot["criteria"]), 3)
        submitted = self.c.post(f"/v1/student/open-assignments/{assignment_id}/submit", headers=S,
                                json={"response": "Desarrollo y justificación."})
        self.assertEqual(submitted.status_code, 200, submitted.text)
        submission_id = self.c.get(
            f"/v1/teacher/open-assignments/{assignment_id}/submissions", headers=T
        ).json()["submissions"][0]["id"]
        rejected = self.c.post(f"/v1/teacher/open-submissions/{submission_id}/grade", headers=T,
                               json={"score": 80, "rubric": {"interpretacion": 3}})
        self.assertEqual(rejected.status_code, 400, rejected.text)
        scores = {criterion["id"]: 3 for criterion in snapshot["criteria"]}
        graded = self.c.post(f"/v1/teacher/open-submissions/{submission_id}/grade", headers=T,
                             json={"score": 80, "feedback": "Buen trabajo.", "rubric": scores})
        self.assertEqual(graded.status_code, 200, graded.text)
        result = self.c.get(f"/v1/student/open-submissions/{submission_id}", headers=S)
        self.assertEqual(result.json()["rubric_snapshot"], snapshot)
        self.assertEqual(result.json()["rubric"], scores)

    def test_open_assignment_deadline_validation_and_expiration_over_http(self):
        item = next((i for i in M.BANK.items.values() if i.kind == "open"), None)
        if item is None:
            self.skipTest("el banco de pruebas no contiene ítems abiertos")
        invalid = self.c.post("/v1/teacher/open-assignments", headers=T, json={
            "item_id": item.id, "title": "Fecha sin zona", "due_at": "2099-01-01T12:00:00"
        })
        self.assertEqual(invalid.status_code, 400, invalid.text)

        assignment_id = "http-expired-deadline"
        M.STORE.create_open_assignment(assignment_id, "escuela-h", None, item.id,
                                       "Actividad vencida", "", "teacher", "2000-01-01T00:00:00+00:00")
        listed = self.c.get("/v1/student/open-assignments", headers=S)
        self.assertEqual(listed.status_code, 200, listed.text)
        expired = next(a for a in listed.json()["assignments"] if a["id"] == assignment_id)
        self.assertTrue(expired["expired"])
        submitted = self.c.post(f"/v1/student/open-assignments/{assignment_id}/submit", headers=S,
                                json={"response": "Intento fuera de plazo"})
        self.assertEqual(submitted.status_code, 410, submitted.text)

    def test_review_over_http(self):
        self.assertEqual(self.c.get("/v1/review/templates", headers=S).status_code, 403)
        self.assertEqual(self.c.get("/v1/review/templates", headers=T).status_code, 403)
        lst = self.c.get("/v1/review/templates", headers=A).json()
        self.assertEqual(len(lst["templates"]), 24)
        self.assertEqual(self.c.get("/v1/review/templates/ZZ/sample", headers=A).status_code, 404)
        r = self.c.post("/v1/review/templates/T7", json={"decision": "aprobar", "checklist": {}}, headers=A)
        self.assertEqual(r.status_code, 400)
        valid = {"decision": "aprobar", "checklist": {k: True for k in M.CHECKLIST}}
        first = self.c.post("/v1/review/templates/T7", json=valid, headers=A)
        self.assertEqual(first.status_code, 200)
        duplicate = self.c.post("/v1/review/templates/T7", json=valid, headers=A)
        self.assertEqual(duplicate.status_code, 409)

    def test_new_endpoints_over_http(self):
        r = self.c.post("/v1/sessions", json={"mode": "dirigida", "skill": "porcentajes"}, headers=S)
        self.assertEqual(r.status_code, 200, r.text)
        sid, item_id = r.json()["session_id"], r.json()["items"][0]["id"]
        h = self.c.get(f"/v1/sessions/{sid}/hint", params={"item_id": item_id, "level": 1}, headers=S)
        self.assertEqual(h.status_code, 200, h.text)
        item = M.BANK.items[item_id]
        a = self.c.post(f"/v1/sessions/{sid}/answers", json={"item_id": item_id, "response": str(item.correct)}, headers=S)
        self.assertTrue(a.json()["correct"] and a.json()["explanation"])
        self.assertEqual(self.c.get("/v1/me/progress", headers=S).json()["responses"] >= 1, True)
        self.assertEqual(self.c.get("/v1/teacher/courses", headers=T).status_code, 200)
        csv = self.c.get("/v1/teacher/export.csv", headers=T)
        self.assertEqual(csv.status_code, 200)
        self.assertIn("text/csv", csv.headers["content-type"])
        self.assertEqual(self.c.get("/v1/teacher/export.csv", headers=S).status_code, 403)
        self.assertIn("x-request-id", self.c.get("/healthz").headers)
        self.assertIn("matheval_requests_total", self.c.get("/metrics").text)
        self.assertEqual(self.c.delete("/v1/me/data", headers=S).status_code, 200)

    def test_school_can_withdraw_network_consent_over_http(self):
        invited = self.c.post("/v1/network/tenants", json={"tenant_id": "escuela-h"}, headers=N)
        self.assertEqual(invited.status_code, 200, invited.text)
        pending = self.c.get("/v1/teacher/network-invites", headers=T).json()
        self.assertEqual(pending["invites"], ["red-http"])
        accepted = self.c.post("/v1/teacher/network-invites/red-http/accept", headers=T)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(self.c.get("/v1/teacher/network-memberships", headers=T).json()["networks"], ["red-http"])
        denied = self.c.delete("/v1/teacher/network-memberships/red-http", headers=S)
        self.assertEqual(denied.status_code, 403)
        revoked = self.c.delete("/v1/teacher/network-memberships/red-http", headers=T)
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(revoked.json()["networks"], [])
        self.assertEqual(self.c.get("/v1/network/summary", headers=N).json()["schools"], [])

    def test_lti_exchange_gives_working_bearer(self):
        handoff = jwt.encode({"sub": "u-http", "tenant_id": "dep-http", "role": "student",
                             "iss": "matheval-lti", "aud": "matheval-api", "iat": int(time.time()),
                             "jti": "http-handoff-1", "exp": int(time.time()) + 60},
                             os.environ["LTI_HANDOFF_SECRET"], algorithm="HS256")
        r = self.c.post("/v1/lti/exchange", json={"token": handoff})
        self.assertEqual(r.status_code, 200)
        h = {"Authorization": "Bearer " + r.json()["access_token"]}
        self.assertEqual(self.c.post("/v1/sessions", json={"mode": "practica"}, headers=h).status_code, 200)
        self.assertEqual(self.c.post("/v1/lti/exchange", json={"token": "basura"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()

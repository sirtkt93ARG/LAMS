"""Pruebas por HTTP con el TestClient de FastAPI (requiere fastapi y httpx reales; si no están, se omiten)."""
import os, sys, tempfile, time, unittest
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

    def test_review_over_http(self):
        self.assertEqual(self.c.get("/v1/review/templates", headers=S).status_code, 403)
        self.assertEqual(self.c.get("/v1/review/templates", headers=T).status_code, 403)
        lst = self.c.get("/v1/review/templates", headers=A).json()
        self.assertEqual(len(lst["templates"]), 24)
        self.assertEqual(self.c.get("/v1/review/templates/ZZ/sample", headers=A).status_code, 404)
        r = self.c.post("/v1/review/templates/T7", json={"decision": "aprobar", "checklist": {}}, headers=A)
        self.assertEqual(r.status_code, 400)

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

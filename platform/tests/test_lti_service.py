"""Prueba la lógica propia del servicio LTI (rol, tenant, token de traspaso) con sustitutos de PyLTI1p3 y
Flask-Caching: así corre igual con o sin esas librerías instaladas."""
import importlib.util, os, sys, types, unittest
sys.path.insert(0, os.getcwd())
import jwt

os.environ.update({"MATHEVAL_DEV": "1", "LTI_SECRET_KEY": "k" * 40, "LTI_HANDOFF_SECRET": "h" * 40, "WEB_URL": "http://web.test", "LTI_CONFIG": "no-existe/x.json"})
R = "https://purl.imsglobal.org/spec/lti/claim/roles"
D = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
NRPS = "https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice"


def _fakes():
    class Launch:
        data = {}
        def __init__(self, *a, **k): pass
        def get_launch_data(self): return Launch.data
    class Login:
        def __init__(self, *a, **k): pass
        def enable_check_cookies(self): return self
        def redirect(self, target):
            from flask import redirect
            return redirect("http://lms.test/auth?target=" + str(target))
    class Cache:
        def __init__(self, app): pass
    mods = {
        "flask_caching": types.SimpleNamespace(Cache=Cache),
        "pylti1p3": types.ModuleType("pylti1p3"),
        "pylti1p3.contrib": types.ModuleType("pylti1p3.contrib"),
        "pylti1p3.contrib.flask": types.SimpleNamespace(FlaskCacheDataStorage=lambda c: None, FlaskMessageLaunch=Launch,
                                                        FlaskOIDCLogin=Login, FlaskRequest=lambda: None),
        "pylti1p3.tool_config": types.SimpleNamespace(ToolConfJsonFile=lambda p: types.SimpleNamespace(get_jwks=lambda: {"keys": []})),
    }
    return mods, Launch


@unittest.skipUnless(importlib.util.find_spec("flask"), "Flask no instalado")
class TestLtiService(unittest.TestCase):
    def setUp(self):
        mods, self.Launch = _fakes()
        self.saved = {k: sys.modules.get(k) for k in list(mods) + ["lti_service.app"]}
        sys.modules.pop("lti_service.app", None)
        sys.modules.update(mods)
        self.mod = importlib.import_module("lti_service.app")
        self.c = self.mod.app.test_client()

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None: sys.modules.pop(k, None)
            else: sys.modules[k] = v

    def _token(self, resp):
        loc = resp.headers["Location"]
        self.assertTrue(loc.startswith("http://web.test/lti/enter?token="))
        return jwt.decode(loc.split("token=")[1], "h" * 40, algorithms=["HS256"], issuer="matheval-lti", audience="matheval-api")

    def test_teacher_and_student_roles_and_tenant(self):
        self.Launch.data = {"sub": "u1", "iss": "http://lms", D: "dep-7", R: ["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
                            "aud": "client-1", NRPS: {"context_memberships_url": "https://lms.test/members", "service_versions": ["2.0"]}}
        t = self._token(self.c.post("/lti/launch/"))
        self.assertEqual((t["role"], t["tenant_id"], t["sub"]), ("teacher", "dep-7", "u1"))
        self.assertTrue(t["jti"])
        self.assertEqual((t["iss"], t["aud"]), ("matheval-lti", "matheval-api"))
        self.assertEqual(t["nrps"], {"iss": "http://lms", "client_id": "client-1",
                                     "context_memberships_url": "https://lms.test/members"})
        self.Launch.data = {"sub": "u2", "iss": "http://lms", D: "dep-7", R: ["http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"]}
        student_token = self._token(self.c.post("/lti/launch/"))
        self.assertEqual(student_token["role"], "student")
        self.assertNotIn("nrps", student_token)

    def test_incomplete_launch_is_400_and_token_is_short_lived(self):
        self.Launch.data = {"sub": "u1", "iss": "x"}                       # falta deployment_id
        self.assertEqual(self.c.post("/lti/launch/").status_code, 400)
        self.Launch.data = {"sub": "u1", "iss": "x", D: "d", R: []}
        t = self._token(self.c.post("/lti/launch/"))
        self.assertLessEqual(t["exp"] - __import__("time").time(), 61)

    def test_nrps_proxy_requires_internal_secret_and_returns_only_minimal_roster(self):
        payload = {"nrps": {"iss": "http://lms", "client_id": "client-1",
                            "context_memberships_url": "https://lms.test/members"}}
        self.assertEqual(self.c.post("/lti/nrps/roster", json=payload).status_code, 401)
        registration = {"public_pem": b"public", "private_pem": b"private",
                        "auth_token_url": "https://lms.test/token", "nrps_allowed_hosts": ["lms.test"]}
        with patch.object(self.mod, "tool_registration", return_value=registration), \
             patch.object(self.mod.ags, "public_jwk", return_value={"kid": "key-1"}), \
             patch.object(self.mod.nrps, "fetch_roster", return_value=[{"user_id": "u1", "name": "Alumno Uno"}]) as fetch:
            response = self.c.post("/lti/nrps/roster", json=payload,
                                    headers={"X-Internal-Secret": "h" * 40})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json(), {"members": [{"user_id": "u1", "name": "Alumno Uno"}]})
        fetch.assert_called_once()

    def test_login_redirects_and_jwks(self):
        r = self.c.post("/lti/login/", data={"target_link_uri": "http://tool/lti/launch/"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.c.get("/lti/jwks/").get_json(), {"keys": []})


if __name__ == "__main__":
    unittest.main()

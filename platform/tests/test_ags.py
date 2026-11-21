"""Prueba real por HTTP (en localhost) del cliente de notas contra el LMS simulado."""
import os, sys, threading, unittest, urllib.error
sys.path.insert(0, os.getcwd())
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

HAS_FLASK = __import__("importlib").util.find_spec("flask") is not None


def _keys():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return priv, pub


@unittest.skipUnless(HAS_FLASK, "Flask no instalado")
class TestAgs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from werkzeug.serving import make_server
        from lti_service import ags
        from tools.mock_lms.app import app
        cls.ags, cls.app = ags, app
        cls.priv, cls.pub = _keys()
        app.config["TOOL_JWKS_FETCH"] = lambda: {"keys": [ags.public_jwk(cls.pub)]}
        cls.srv = make_server("127.0.0.1", 0, app)
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_scores_url_keeps_query(self):
        self.assertEqual(self.ags.scores_url("http://l/x/lineitem?type_id=3"), "http://l/x/lineitem/scores?type_id=3")
        self.assertEqual(self.ags.scores_url("http://l/lineitems/1/"), "http://l/lineitems/1/scores")

    def test_full_grade_passback(self):
        kid = self.ags.public_jwk(self.pub)["kid"]
        tok = self.ags.get_access_token(self.base + "/token", "mock-client", self.priv, kid)
        status = self.ags.post_score(self.base + "/lineitems/1", tok, "alumno-ags", 6, 8, "Nivel N6 (preliminar)")
        self.assertEqual(status, 200)
        page = self.app.test_client().get("/gradebook").get_data(as_text=True)
        self.assertIn("alumno-ags", page)
        self.assertIn("6 / 8", page)

    def test_rejections(self):
        other_priv, other_pub = _keys()
        kid = self.ags.public_jwk(self.pub)["kid"]
        with self.assertRaises(urllib.error.HTTPError) as c:                   # firmada con otra clave
            self.ags.get_access_token(self.base + "/token", "mock-client", other_priv, kid)
        self.assertEqual(c.exception.code, 401)
        with self.assertRaises(urllib.error.HTTPError) as c:                   # token inexistente
            self.ags.post_score(self.base + "/lineitems/1", "falso", "u", 1, 8)
        self.assertEqual(c.exception.code, 401)
        with self.assertRaises(urllib.error.HTTPError) as c:                   # otro cliente
            self.ags.get_access_token(self.base + "/token", "otro-cliente", self.priv, kid)
        self.assertEqual(c.exception.code, 401)


if __name__ == "__main__":
    unittest.main()

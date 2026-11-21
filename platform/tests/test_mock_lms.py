import importlib.util
import os, re, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, os.getcwd())
import jwt
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from lti_service.ags import public_jwk
from tools.mock_lms.platform import CLAIM, MockPlatform


class TestMockPlatform(unittest.TestCase):
    def test_token_verifies_with_published_jwks(self):
        p = MockPlatform("http://lms.test", "cli", "dep-1")
        tok = p.build_id_token(sub="u1", role="teacher", nonce="n123", target_link_uri="http://tool/launch/")
        key = RSAAlgorithm.from_jwk(p.jwks()["keys"][0])
        c = jwt.decode(tok, key, algorithms=["RS256"], audience="cli", issuer="http://lms.test")
        self.assertEqual((c["sub"], c["nonce"], c[CLAIM + "deployment_id"]), ("u1", "n123", "dep-1"))
        self.assertIn("Instructor", c[CLAIM + "roles"][0])
        self.assertEqual(jwt.get_unverified_header(tok)["kid"], p.jwks()["keys"][0]["kid"])

    def test_mock_lms_reads_tool_public_key_without_http_callback(self):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "tool-public.pem"
            key_path.write_bytes(public_pem)
            with patch.dict(os.environ, {"TOOL_PUBLIC_KEY_FILE": str(key_path)}):
                from tools.mock_lms.app import _tool_jwks
                actual = _tool_jwks()["keys"][0]
        self.assertEqual(actual, public_jwk(public_pem))

    def test_wrong_key_is_rejected(self):
        a, b = MockPlatform("i", "c", "d"), MockPlatform("i", "c", "d")
        tok = a.build_id_token(sub="u", role="student", nonce="n", target_link_uri="t")
        with self.assertRaises(jwt.PyJWTError):
            jwt.decode(tok, RSAAlgorithm.from_jwk(b.jwks()["keys"][0]), algorithms=["RS256"], audience="c", issuer="i")


@unittest.skipUnless(importlib.util.find_spec("flask"), "Flask no instalado")
class TestMockApp(unittest.TestCase):
    def setUp(self):
        from tools.mock_lms.app import app
        self.c = app.test_client()

    def test_index_and_jwks(self):
        self.assertIn("Entrar como docente", self.c.get("/").get_data(as_text=True))
        self.assertEqual(self.c.get("/jwks").get_json()["keys"][0]["kty"], "RSA")

    def test_auth_returns_autosubmit_form_with_token(self):
        r = self.c.post("/auth", data={"client_id": "mock-client", "redirect_uri": "http://localhost:8200/lti/launch/",
                                       "login_hint": "alumno-9", "lti_message_hint": "student", "nonce": "abc", "state": "st1"})
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('action="http://localhost:8200/lti/launch/"', html)
        tok = re.search(r'name="id_token" value="([^"]+)"', html).group(1)
        self.assertEqual(jwt.decode(tok, options={"verify_signature": False})["sub"], "alumno-9")
        self.assertIn('name="state" value="st1"', html)

    def test_auth_rejects_unregistered_targets(self):
        for bad in ({"client_id": "otro", "redirect_uri": "http://localhost:8200/x"},
                    {"client_id": "mock-client", "redirect_uri": "http://evil.example/launch"}):
            self.assertEqual(self.c.post("/auth", data=bad).status_code, 400)


if __name__ == "__main__":
    unittest.main()

import time
import unittest

import jwt
from fastapi import HTTPException

from api.app import auth
from api.app.security import check_config


class TestProductionConfig(unittest.TestCase):
    def test_development_mode_is_explicitly_warned(self):
        errors, warnings = check_config({}, True)
        self.assertEqual(errors, [])
        self.assertTrue(any("MATHEVAL_DEV=1" in x for x in warnings))

    def test_production_requires_strong_pseudonym_secret_and_auth(self):
        errors, _ = check_config({}, False)
        self.assertTrue(any("PSEUDONYM_SECRET" in x for x in errors))
        self.assertTrue(any("autenticación" in x for x in errors))

    def test_oidc_production_config_accepts_strong_secret_and_https(self):
        env = {
            "PSEUDONYM_SECRET": "p" * 48,
            "OIDC_ISSUER": "https://identity.example/realms/matheval",
            "WEB_ORIGIN": "https://app.example",
            "DATABASE_URL": "postgresql://app:secret@db.example/matheval",
        }
        errors, _ = check_config(env, False)
        self.assertEqual(errors, [])

    def test_production_rejects_nonlocal_http_origins(self):
        env = {
            "PSEUDONYM_SECRET": "p" * 48,
            "OIDC_ISSUER": "http://identity.example/realms/matheval",
            "WEB_ORIGIN": "http://app.example",
            "DATABASE_URL": "postgresql://app:secret@db.example/matheval",
        }
        errors, _ = check_config(env, False)
        self.assertTrue(any("OIDC_ISSUER" in x for x in errors))
        self.assertTrue(any("WEB_ORIGIN" in x for x in errors))

    def test_production_rejects_development_secrets_even_when_long(self):
        env = {
            "PSEUDONYM_SECRET": "dev-pseudonym-secret-cambiar-0123456789abcdef",
            "LTI_HANDOFF_SECRET": "dev-handoff-secret-cambiar-0123456789abcdef",
            "SESSION_SECRET": "dev-session-secret-cambiar-0123456789abcdef",
            "LTI_SECRET_KEY": "k" * 48,
            "WEB_ORIGIN": "https://app.example",
            "WEB_URL": "https://app.example",
            "DATABASE_URL": "postgresql://app:secret@db.example/matheval",
        }
        errors, _ = check_config(env, False)
        self.assertTrue(any("PSEUDONYM_SECRET" in x for x in errors))
        self.assertTrue(any("LTI_HANDOFF_SECRET" in x for x in errors))
        self.assertTrue(any("SESSION_SECRET" in x for x in errors))

    def test_api_lti_config_does_not_require_flask_service_secret(self):
        env = {
            "PSEUDONYM_SECRET": "p" * 48,
            "LTI_HANDOFF_SECRET": "h" * 48,
            "SESSION_SECRET": "s" * 48,
            "WEB_ORIGIN": "https://app.example",
            "DATABASE_URL": "postgresql://app:secret@db.example/matheval",
            "WEB_URL": "https://app.example",
        }
        errors, _ = check_config(env, False)
        self.assertEqual(errors, [])


    def test_production_rejects_lookalike_localhost_redirect(self):
        env = {
            "PSEUDONYM_SECRET": "p" * 48,
            "LTI_HANDOFF_SECRET": "h" * 48,
            "SESSION_SECRET": "s" * 48,
            "WEB_ORIGIN": "https://app.example",
            "WEB_URL": "http://localhost.attacker.example",
            "DATABASE_URL": "postgresql://app:secret@db.example/matheval",
        }
        errors, _ = check_config(env, False)
        self.assertTrue(any("WEB_URL" in x for x in errors))


class TestOneTimeHandoff(unittest.TestCase):
    def setUp(self):
        self.old_secret = auth.HANDOFF_SECRET
        self.old_consumer = auth._token_consumer
        auth.HANDOFF_SECRET = "h" * 48

    def tearDown(self):
        auth.HANDOFF_SECRET = self.old_secret
        auth.set_token_consumer(self.old_consumer)

    def token(self, **overrides):
        now = int(time.time())
        claims = {
            "sub": "student-1", "tenant_id": "school-1", "role": "student",
            "iss": "matheval-lti", "aud": "matheval-api",
            "iat": now, "exp": now + 60, "jti": "handoff-123",
        }
        claims.update(overrides)
        return jwt.encode(claims, auth.HANDOFF_SECRET, algorithm="HS256")

    def test_valid_token_is_consumed_and_user_is_returned(self):
        seen = []
        auth.set_token_consumer(lambda jti: seen.append(jti) or True)
        user = auth.verify_handoff(self.token())
        self.assertEqual((user.sub, user.tenant_id, user.role), ("student-1", "school-1", "student"))
        self.assertEqual(seen, ["handoff-123"])

    def test_nrps_context_survives_one_time_handoff_and_session_minting(self):
        old_session = auth.SESSION_SECRET
        auth.SESSION_SECRET = "s" * 48
        nrps = {"iss": "https://lms.example", "client_id": "client-1",
                "context_memberships_url": "https://lms.example/api/members"}
        auth.set_token_consumer(lambda _jti: True)
        try:
            user = auth.verify_handoff(self.token(nrps=nrps, role="teacher"))
            self.assertEqual(user.nrps, nrps)
            session = auth.mint_session_token(user)
            restored = auth.current_user("Bearer " + session, None)
            self.assertEqual(restored.nrps, nrps)
        finally:
            auth.SESSION_SECRET = old_session

    def test_replayed_token_is_rejected(self):
        auth.set_token_consumer(lambda _jti: False)
        with self.assertRaises(HTTPException) as ctx:
            auth.verify_handoff(self.token())
        self.assertEqual(ctx.exception.status_code, 401)

    def test_token_without_jti_is_rejected(self):
        auth.set_token_consumer(lambda _jti: True)
        with self.assertRaises(HTTPException) as ctx:
            auth.verify_handoff(self.token(jti=None))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_missing_consumer_fails_closed(self):
        auth.set_token_consumer(None)
        with self.assertRaises(HTTPException) as ctx:
            auth.verify_handoff(self.token())
        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()

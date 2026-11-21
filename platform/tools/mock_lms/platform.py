"""Plataforma LTI 1.3 de juguete (lado del LMS) para probar el servicio LTI sin instalar Moodle.
Solo para desarrollo: genera una clave RSA al arrancar y firma lanzamientos de 'Práctica de matemática'."""
from __future__ import annotations
import json
import time
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

CLAIM = "https://purl.imsglobal.org/spec/lti/claim/"
CLAIM_AGS = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
SCOPE_SCORE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
ROLE_STUDENT = "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
ROLE_TEACHER = "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"


class MockPlatform:
    def __init__(self, issuer: str, client_id: str, deployment_id: str, kid: str = "mock-key-1"):
        self.issuer, self.client_id, self.deployment_id, self.kid = issuer, client_id, deployment_id, kid
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def jwks(self) -> dict:
        jwk = json.loads(RSAAlgorithm.to_jwk(self._key.public_key()))
        jwk.update({"kid": self.kid, "alg": "RS256", "use": "sig"})
        return {"keys": [jwk]}

    def build_id_token(self, *, sub: str, role: str, nonce: str, target_link_uri: str, ttl: int = 300,
                       course: dict | None = None, lineitem: str | None = None) -> str:
        now = int(time.time())
        claims = {
            "iss": self.issuer, "aud": self.client_id, "sub": sub, "iat": now, "exp": now + ttl, "nonce": nonce,
            CLAIM + "message_type": "LtiResourceLinkRequest",
            CLAIM + "version": "1.3.0",
            CLAIM + "deployment_id": self.deployment_id,
            CLAIM + "target_link_uri": target_link_uri,
            CLAIM + "resource_link": {"id": "mock-resource-1", "title": "Práctica de matemática"},
            CLAIM + "roles": [ROLE_TEACHER if role == "teacher" else ROLE_STUDENT],
        }
        if course:
            claims[CLAIM + "context"] = course
        if lineitem:
            claims[CLAIM_AGS] = {"scope": [SCOPE_SCORE], "lineitem": lineitem}
        return jwt.encode(claims, self._key, algorithm="RS256", headers={"kid": self.kid})

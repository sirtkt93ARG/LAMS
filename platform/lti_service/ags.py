"""LTI Advantage - Assignment and Grade Services (devolución de notas al libro de calificaciones del LMS).
Autenticación OAuth2 con credenciales de cliente y aserción JWT firmada (RFC 7523). Sin dependencias de PyLTI1p3."""
from __future__ import annotations
import base64
import hashlib
import json
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
import jwt
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm

SCOPE_SCORE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def public_jwk(public_pem: bytes) -> dict:
    """JWK público con kid estable (huella de la clave): lo publica el servicio y lo usa la aserción."""
    jwk = json.loads(RSAAlgorithm.to_jwk(serialization.load_pem_public_key(public_pem)))
    kid = _b64(hashlib.sha256(json.dumps({"e": jwk["e"], "kty": "RSA", "n": jwk["n"]}, separators=(",", ":")).encode()).digest())[:22]
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return jwk


def client_assertion(client_id: str, token_url: str, private_pem: bytes, kid: str) -> str:
    now = int(time.time())
    return jwt.encode({"iss": client_id, "sub": client_id, "aud": token_url, "iat": now, "exp": now + 60, "jti": str(uuid.uuid4())},
                      serialization.load_pem_private_key(private_pem, None), algorithm="RS256", headers={"kid": kid})


def get_access_token(token_url: str, client_id: str, private_pem: bytes, kid: str, scope: str = SCOPE_SCORE, timeout: float = 10) -> str:
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_assertion_type": ASSERTION_TYPE,
                                   "client_assertion": client_assertion(client_id, token_url, private_pem, kid), "scope": scope}).encode()
    req = urllib.request.Request(token_url, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:                       # noqa: S310 (URL de la configuración del LMS)
        return json.loads(r.read())["access_token"]


def scores_url(lineitem: str) -> str:
    u = urllib.parse.urlsplit(lineitem)
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path.rstrip("/") + "/scores", u.query, ""))


def post_score(lineitem: str, token: str, user_id: str, given: float, maximum: float, comment: str = "", timeout: float = 10) -> int:
    payload = {"userId": user_id, "scoreGiven": given, "scoreMaximum": maximum, "comment": comment,
               "activityProgress": "Completed", "gradingProgress": "FullyGraded",
               "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    req = urllib.request.Request(scores_url(lineitem), data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/vnd.ims.lis.v1.score+json", "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:                       # noqa: S310
        return r.status

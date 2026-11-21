"""Autenticación: Keycloak (JWT RS256), sesiones propias del acceso por LTI (HS256) y modo desarrollo."""
from __future__ import annotations
import os
import time
from dataclasses import dataclass
import jwt
from fastapi import Header, HTTPException

DEV = os.getenv("MATHEVAL_DEV") == "1"
ISSUER = os.getenv("OIDC_ISSUER", "")                 # p. ej. http://keycloak:8080/realms/matheval
AUDIENCE = os.getenv("OIDC_AUDIENCE", "matheval-api")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")      # firma las sesiones emitidas tras un acceso LTI
HANDOFF_SECRET = os.getenv("LTI_HANDOFF_SECRET", "")  # compartido con lti_service (token de 60 s)
SESSION_TTL_S = 2 * 3600
_token_consumer = None


def set_token_consumer(fn) -> None:
    """Inyecta el almacén que consume los identificadores únicos de los handoffs LTI."""
    global _token_consumer
    _token_consumer = fn


_jwks = jwt.PyJWKClient(f"{ISSUER}/protocol/openid-connect/certs") if ISSUER else None


@dataclass
class User:
    sub: str
    tenant_id: str
    role: str  # student | teacher | admin | network
    course_id: str | None = None
    course_label: str | None = None
    ags: dict | None = None    # datos para devolver la nota al LMS (LTI Advantage); solo en accesos por LTI


def verify_handoff(token: str) -> User:
    if not HANDOFF_SECRET:
        raise HTTPException(503, "LTI no configurado")
    try:
        c = jwt.decode(
            token, HANDOFF_SECRET, algorithms=["HS256"],
            issuer="matheval-lti", audience="matheval-api",
            options={"require": ["sub", "tenant_id", "role", "exp", "iat", "iss", "aud", "jti"]},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(401, "token de acceso inválido o vencido") from e
    if c.get("role") not in ("student", "teacher", "admin"):
        raise HTTPException(403, "rol no permitido")
    if not isinstance(c.get("jti"), str) or not c["jti"].strip():
        raise HTTPException(401, "token de acceso sin identificador único")
    if _token_consumer is None:
        raise HTTPException(503, "protección de reutilización LTI no configurada")
    if not _token_consumer(c["jti"]):
        raise HTTPException(401, "token de acceso ya utilizado")
    return User(c["sub"], c["tenant_id"], c["role"], c.get("course_id"), c.get("course_label"), c.get("ags"))


def mint_session_token(u: User) -> str:
    if not SESSION_SECRET:
        raise HTTPException(503, "SESSION_SECRET no configurado")
    now = int(time.time())
    claims = {"sub": u.sub, "tenant_id": u.tenant_id, "role": u.role, "iss": "matheval-lti", "aud": AUDIENCE,
              "iat": now, "exp": now + SESSION_TTL_S}
    for k in ("course_id", "course_label", "ags"):
        if getattr(u, k):
            claims[k] = getattr(u, k)
    return jwt.encode(claims, SESSION_SECRET, algorithm="HS256")


def current_user(authorization: str | None = Header(default=None), x_dev_user: str | None = Header(default=None)) -> User:
    if DEV and x_dev_user:                       # formato: sub:tenant:rol  (solo desarrollo)
        parts = x_dev_user.split(":")
        if len(parts) != 3 or parts[2] not in ("student", "teacher", "admin", "network"):
            raise HTTPException(400, "X-Dev-User debe ser sub:tenant:rol")
        return User(*parts)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "no autenticado")
    token = authorization[7:]
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":
            if not SESSION_SECRET:
                raise HTTPException(401, "token inválido")
            c = jwt.decode(token, SESSION_SECRET, algorithms=["HS256"], audience=AUDIENCE, issuer="matheval-lti")
            return User(c["sub"], c["tenant_id"], c["role"], c.get("course_id"), c.get("course_label"), c.get("ags"))
        if _jwks is None:
            raise HTTPException(401, "no autenticado")
        key = _jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER)
    except jwt.PyJWTError as e:
        raise HTTPException(401, "token inválido") from e
    roles = claims.get("realm_access", {}).get("roles", [])
    role = "admin" if "admin" in roles else "network" if "network" in roles else "teacher" if "teacher" in roles else "student"
    if "tenant_id" not in claims:
        raise HTTPException(403, "el token no incluye tenant_id")
    return User(claims["sub"], claims["tenant_id"], role)

"""Servicio LTI 1.3 (Flask + PyLTI1p3). Recibe el lanzamiento desde el LMS, lo valida, mapea el rol y redirige a la
web con un token de un solo uso (60 s). El identificador de la escuela (tenant) es el deployment_id del LMS.
Probado aquí con sustitutos de PyLTI1p3; la validación real contra un LMS se hace con el LMS simulado
(tools/mock_lms) o con Moodle."""
import json
import hmac
import logging
import os
import pathlib
import time
import uuid
from urllib.parse import urlparse
import jwt
from flask import Flask, jsonify, redirect, request
from flask_caching import Cache
from pylti1p3.contrib.flask import FlaskCacheDataStorage, FlaskMessageLaunch, FlaskOIDCLogin, FlaskRequest
from pylti1p3.tool_config import ToolConfJsonFile

from . import ags, nrps

log = logging.getLogger("lti")
app = Flask(__name__)
app.config.update(CACHE_TYPE="SimpleCache", SECRET_KEY=os.environ["LTI_SECRET_KEY"])
cache = Cache(app)
TOOL_CONF = ToolConfJsonFile(os.getenv("LTI_CONFIG", "lti_service/configs/lti.json"))
WEB_URL = os.getenv("WEB_URL", "")
HANDOFF_SECRET = os.environ["LTI_HANDOFF_SECRET"]
DEV = os.getenv("MATHEVAL_DEV") == "1"
if not DEV:
    if len(app.config["SECRET_KEY"]) < 32 or len(HANDOFF_SECRET) < 32:
        raise RuntimeError("LTI_SECRET_KEY y LTI_HANDOFF_SECRET deben tener al menos 32 caracteres en producción")
    if not WEB_URL:
        raise RuntimeError("WEB_URL es obligatorio cuando LTI está habilitado")
    web_url = urlparse(WEB_URL)
    if web_url.scheme == "http" and web_url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("WEB_URL debe usar HTTPS fuera de localhost")
ROLES = "https://purl.imsglobal.org/spec/lti/claim/roles"
DEPLOYMENT = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
CONTEXT = "https://purl.imsglobal.org/spec/lti/claim/context"
AGS_ENDPOINT = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
NRPS_CLAIM = "https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice"
CONFIG_PATH = pathlib.Path(os.getenv("LTI_CONFIG", "lti_service/configs/lti.json"))


def tool_registration(iss: str, client_id: str) -> dict:
    """Entrada de configuración del LMS (con las rutas de las claves resueltas respecto de la carpeta del archivo)."""
    for conf in json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get(iss, []):
        if conf["client_id"] == client_id:
            d = CONFIG_PATH.parent
            return {**conf, "private_pem": (d / conf["private_key_file"]).read_bytes(), "public_pem": (d / conf["public_key_file"]).read_bytes()}
    raise KeyError(f"LMS no registrado: {iss} / {client_id}")


def role_of(roles: list[str]) -> str:
    return "teacher" if any(("Instructor" in r or "Administrator" in r) for r in roles) else "student"


@app.route("/lti/login/", methods=["GET", "POST"])
def login():
    storage = FlaskCacheDataStorage(cache)
    oidc = FlaskOIDCLogin(FlaskRequest(), TOOL_CONF, launch_data_storage=storage)
    if os.getenv("LTI_CHECK_COOKIES") == "1":          # en iframes de un LMS real; en local conviene dejarlo apagado
        oidc = oidc.enable_check_cookies()
    return oidc.redirect(request.values.get("target_link_uri"))


@app.route("/lti/launch/", methods=["GET", "POST"])
def launch():
    try:
        storage = FlaskCacheDataStorage(cache)
        data = FlaskMessageLaunch(FlaskRequest(), TOOL_CONF, launch_data_storage=storage).get_launch_data()
        tenant = data[DEPLOYMENT]
        claims = {"sub": data["sub"], "iss": "matheval-lti", "aud": "matheval-api",
                  "jti": uuid.uuid4().hex, "role": role_of(data.get(ROLES, [])),
                  "tenant_id": tenant, "iat": int(time.time()), "exp": int(time.time()) + 60}
        ctx = data.get(CONTEXT) or {}
        if ctx.get("id"):
            claims["course_id"], claims["course_label"] = str(ctx["id"]), str(ctx.get("label") or ctx.get("title") or ctx["id"])
        ep = data.get(AGS_ENDPOINT) or {}
        aud = data.get("aud")
        client_id = aud[0] if isinstance(aud, list) else aud
        if ep.get("lineitem") and ags.SCOPE_SCORE in ep.get("scope", []):
            claims["ags"] = {"iss": data["iss"], "client_id": client_id, "lineitem": ep["lineitem"]}
        nrps_claim = data.get(NRPS_CLAIM) or {}
        memberships_url = nrps_claim.get("context_memberships_url")
        service_versions = nrps_claim.get("service_versions", [])
        if (role_of(data.get(ROLES, [])) == "teacher" and isinstance(memberships_url, str)
                and 0 < len(memberships_url) <= 2048 and isinstance(client_id, str) and client_id
                and isinstance(service_versions, list) and "2.0" in service_versions):
            claims["nrps"] = {"iss": data["iss"], "client_id": client_id,
                              "context_memberships_url": memberships_url}
        token = jwt.encode(claims, HANDOFF_SECRET, algorithm="HS256")
    except Exception as e:                              # validación de PyLTI1p3 fallida o datos incompletos
        log.exception("lanzamiento LTI inválido")
        return jsonify({"error": "lanzamiento LTI inválido", "detail": str(e)}), 400
    return redirect(f"{WEB_URL}/lti/enter?token={token}")


@app.route("/lti/jwks/")
def jwks():
    """Clave pública de la herramienta: la usa el LMS para verificar la aserción de las llamadas de notas."""
    try:
        conf = next(c for confs in json.loads(CONFIG_PATH.read_text(encoding="utf-8")).values() for c in confs)
        return jsonify({"keys": [ags.public_jwk((CONFIG_PATH.parent / conf["public_key_file"]).read_bytes())]})
    except Exception:                                   # noqa: BLE001
        return jsonify(TOOL_CONF.get_jwks())


@app.route("/lti/nrps/roster", methods=["POST"])
def nrps_roster():
    """Uso interno: devuelve únicamente identificador y nombre de alumnos del contexto LTI."""
    if not hmac.compare_digest(request.headers.get("X-Internal-Secret", ""), HANDOFF_SECRET):
        return jsonify({"error": "no autorizado"}), 401
    body = request.get_json(force=True, silent=True) or {}
    if not isinstance(body, dict) or not isinstance(body.get("nrps"), dict):
        return jsonify({"error": "contexto NRPS incompleto"}), 400
    claim = body["nrps"]
    issuer, client_id = claim.get("iss"), claim.get("client_id")
    memberships_url = claim.get("context_memberships_url")
    if not all(isinstance(value, str) and value for value in (issuer, client_id, memberships_url)) or len(memberships_url) > 2048:
        return jsonify({"error": "contexto NRPS incompleto"}), 400
    try:
        reg = tool_registration(issuer, client_id)
        kid = ags.public_jwk(reg["public_pem"])["kid"]
        members = nrps.fetch_roster(
            memberships_url, issuer, client_id, reg["auth_token_url"], reg["private_pem"], kid,
            allowed_hosts=reg.get("nrps_allowed_hosts"), dev=DEV,
        )
    except ValueError as exc:
        return jsonify({"error": "contexto NRPS no permitido", "detail": str(exc)}), 400
    except Exception as exc:                              # noqa: BLE001
        log.exception("no se pudo consultar el roster NRPS")
        return jsonify({"error": "no se pudo consultar el roster NRPS", "detail": str(exc)}), 502
    return jsonify({"members": members})


@app.route("/lti/ags/score", methods=["POST"])
def ags_score():
    """Uso interno (lo llama la API al terminar una práctica): publica la nota en el libro de calificaciones del LMS."""
    if request.headers.get("X-Internal-Secret") != HANDOFF_SECRET:
        return jsonify({"error": "no autorizado"}), 401
    b = request.get_json(force=True)
    try:
        reg = tool_registration(b["iss"], b["client_id"])
        kid = ags.public_jwk(reg["public_pem"])["kid"]
        token = ags.get_access_token(reg["auth_token_url"], b["client_id"], reg["private_pem"], kid)
        status = ags.post_score(b["lineitem"], token, b["user_id"], b["score_given"], b["score_maximum"], b.get("comment", ""))
    except Exception as e:                              # noqa: BLE001
        log.exception("no se pudo publicar la nota")
        return jsonify({"error": "no se pudo publicar la nota", "detail": str(e)}), 502
    return jsonify({"status": status})

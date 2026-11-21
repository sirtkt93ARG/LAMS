"""LMS simulado. Uso: flask --app tools.mock_lms.app run --port 8300
Flujo LTI 1.3: esta página inicia el login (POST a la herramienta) -> la herramienta redirige a /auth ->
/auth devuelve un id_token firmado por formulario auto-enviado a la herramienta."""
import html
import json
import os
import pathlib
import secrets
import time
import urllib.request
import jwt
from flask import Flask, jsonify, request
from jwt.algorithms import RSAAlgorithm
from lti_service.ags import public_jwk
from .platform import SCOPE_SCORE, MockPlatform

ISS = os.getenv("MOCK_ISS", "http://localhost:8300")
TOOL_BASE = os.getenv("TOOL_BASE", "http://localhost:8200").rstrip("/")
TOOL_INTERNAL_BASE = os.getenv("TOOL_INTERNAL_BASE", TOOL_BASE).rstrip("/")
LINEITEM_BASE = os.getenv("MOCK_LINEITEM_BASE", ISS).rstrip("/")
CLIENT_ID, DEPLOYMENT_ID = "mock-client", "mock-deployment-1"

app = Flask(__name__)
P = MockPlatform(ISS, CLIENT_ID, DEPLOYMENT_ID)
COURSE = {"id": "curso-4a", "label": "4.º A", "title": "Matemática 4.º A"}
LINEITEM = f"{LINEITEM_BASE}/lineitems/1"
app.config.update(GRADES=[], TOKENS={}, TOOL_JWKS_FETCH=None)


def _tool_jwks() -> dict:
    # En Compose compartimos solo la clave pública. Evita que /token tenga que
    # llamar de vuelta al servicio LTI mientras este atiende /lti/ags/score.
    public_key_file = os.getenv("TOOL_PUBLIC_KEY_FILE")
    if public_key_file:
        return {"keys": [public_jwk(pathlib.Path(public_key_file).read_bytes())]}
    fetch = app.config["TOOL_JWKS_FETCH"]
    if fetch:
        return fetch()
    with urllib.request.urlopen(f"{TOOL_INTERNAL_BASE}/lti/jwks/", timeout=10) as r:        # noqa: S310
        return json.loads(r.read())

PAGE = """<!doctype html><html lang="es-AR"><meta charset="utf-8"><title>Aula virtual simulada</title>
<style>body{{font:18px system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem}}form{{border:1px solid #999;padding:1rem;margin:1rem 0}}
button{{min-height:44px;padding:0 1rem;font:inherit}}input{{font:inherit;padding:.3rem}}</style>
<h1>Aula virtual simulada</h1><p><a href="/gradebook">Ver libro de calificaciones</a></p><p>Curso de prueba · actividad «Práctica de matemática». Esta página reemplaza a Moodle para probar el ingreso por LTI 1.3.</p>
{forms}"""
FORM = """<form method="post" action="{tool}/lti/login/"><h2>{title}</h2>
<input type="hidden" name="iss" value="{iss}"><input type="hidden" name="client_id" value="{client}">
<input type="hidden" name="lti_deployment_id" value="{dep}"><input type="hidden" name="target_link_uri" value="{tool}/lti/launch/">
<input type="hidden" name="lti_message_hint" value="{role}">
<label>Identificador del usuario en el aula <input name="login_hint" value="{user}"></label>
<p><button type="submit">Abrir la actividad</button></p></form>"""


@app.get("/")
def index():
    forms = "".join(FORM.format(tool=TOOL_BASE, iss=ISS, client=CLIENT_ID, dep=DEPLOYMENT_ID, title=t, role=r, user=u)
                    for t, r, u in (("Entrar como estudiante", "student", "alumno-lms-1"), ("Entrar como docente", "teacher", "docente-lms-1")))
    return PAGE.format(forms=forms)


@app.get("/jwks")
def jwks():
    return jsonify(P.jwks())


@app.route("/auth", methods=["GET", "POST"])
def auth():
    v = request.values
    redirect_uri = v.get("redirect_uri", "")
    if v.get("client_id") != CLIENT_ID or not redirect_uri.startswith(TOOL_BASE + "/"):
        return jsonify({"error": "client_id o redirect_uri no registrados"}), 400
    role = "teacher" if v.get("lti_message_hint") == "teacher" else "student"
    token = P.build_id_token(sub=v.get("login_hint", "usuario-sin-id"), role=role, nonce=v.get("nonce", ""),
                             target_link_uri=redirect_uri, course=COURSE, lineitem=LINEITEM)
    return ('<!doctype html><meta charset="utf-8"><body onload="document.forms[0].submit()">'
            f'<form method="post" action="{html.escape(redirect_uri)}">'
            f'<input type="hidden" name="id_token" value="{html.escape(token)}">'
            f'<input type="hidden" name="state" value="{html.escape(v.get("state", ""))}">'
            '<noscript><button>Continuar</button></noscript></form>')


@app.route("/token", methods=["POST"])
def token():
    """Credenciales de cliente con aserción JWT (RFC 7523), como exige LTI Advantage."""
    v = request.form
    if v.get("grant_type") != "client_credentials" or v.get("client_assertion_type") != "urn:ietf:params:oauth:client-assertion-type:jwt-bearer":
        return jsonify({"error": "invalid_request"}), 400
    try:
        assertion = v["client_assertion"]
        kid = jwt.get_unverified_header(assertion).get("kid")
        jwk = next(k for k in _tool_jwks()["keys"] if k.get("kid") == kid)
        jwt.decode(assertion, RSAAlgorithm.from_jwk(json.dumps(jwk)), algorithms=["RS256"], audience=[request.base_url, ISS], issuer=CLIENT_ID)
    except Exception as e:                                                       # noqa: BLE001
        return jsonify({"error": "invalid_client", "detail": str(e)}), 401
    if SCOPE_SCORE not in v.get("scope", "").split():
        return jsonify({"error": "invalid_scope"}), 400
    tok = secrets.token_urlsafe(24)
    app.config["TOKENS"][tok] = time.time() + 3600
    return jsonify({"access_token": tok, "token_type": "Bearer", "expires_in": 3600, "scope": SCOPE_SCORE})


@app.get("/lineitems/1")
def lineitem():
    return jsonify({"id": LINEITEM, "label": "Práctica de matemática", "scoreMaximum": 8, "resourceLinkId": "mock-resource-1"})


@app.post("/lineitems/1/scores")
def scores():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or app.config["TOKENS"].get(auth[7:], 0) < time.time():
        return jsonify({"error": "no autorizado"}), 401
    b = request.get_json(force=True, silent=True) or {}
    if not {"userId", "scoreGiven", "scoreMaximum"} <= b.keys() or "score+json" not in request.headers.get("Content-Type", ""):
        return jsonify({"error": "puntaje inválido"}), 400
    app.config["GRADES"].append(b)
    return jsonify({"ok": True})


@app.get("/gradebook")
def gradebook():
    rows = "".join(f"<tr><td>{html.escape(str(g['userId']))}</td><td>{g['scoreGiven']} / {g['scoreMaximum']}</td>"
                   f"<td>{html.escape(str(g.get('comment', '')))}</td><td>{html.escape(str(g.get('timestamp', '')))}</td></tr>"
                   for g in app.config["GRADES"]) or "<tr><td colspan=4>Todavía no llegó ninguna nota.</td></tr>"
    return ('<!doctype html><meta charset="utf-8"><title>Libro de calificaciones</title><style>body{font:18px system-ui;max-width:48rem;margin:2rem auto}'
            'td,th{border-bottom:1px solid #aaa;padding:.4rem;text-align:left}</style><h1>Libro de calificaciones</h1><p><a href="/">Volver</a></p>'
            f"<table><tr><th>Usuario</th><th>Nota</th><th>Comentario</th><th>Fecha</th></tr>{rows}</table>")

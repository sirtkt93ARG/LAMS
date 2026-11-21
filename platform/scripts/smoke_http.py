"""Prueba rápida con todo levantado (API 8000, web 3000, servicio LTI 8200, LMS simulado 8300). Solo usa la biblioteca estándar.
Incluye el recorrido completo de LTI: LMS simulado -> servicio LTI -> API -> sesión del estudiante."""
import http.cookiejar, json, re, sys, urllib.error, urllib.parse, urllib.request

API, WEB, LTI, LMS = "http://localhost:8000", "http://localhost:3000", "http://localhost:8200", "http://localhost:8300"
results = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)


def call(method, url, data=None, headers=None, form=False):
    body = None
    h = dict(headers or {})
    if data is not None:
        body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded" if form else "application/json")
    try:
        r = opener.open(urllib.request.Request(url, data=body, headers=h, method=method), timeout=90)
        return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


def check(name, fn):
    try:
        out = fn()
        ok = out is True or out is None
        results.append((name, ok, "" if ok else str(out)[:140]))
    except Exception as e:                       # noqa: BLE001
        results.append((name, False, repr(e)[:140]))


check("API: /healthz", lambda: json.loads(call("GET", API + "/healthz")[2])["ok"])
check("API: CORS para la web", lambda: call("OPTIONS", API + "/v1/sessions", headers={"Origin": WEB, "Access-Control-Request-Method": "POST",
      "Access-Control-Request-Headers": "content-type,authorization"})[1].get("access-control-allow-origin") == WEB)
for path in ("/", "/practice", "/teacher", "/review", "/progress", "/observatory", "/network", "/teacher/report", "/analysis"):
    check(f"Web: {path} responde", lambda p=path: call("GET", WEB + p)[0] == 200)
check("Servicio LTI: /lti/jwks/", lambda: "keys" in json.loads(call("GET", LTI + "/lti/jwks/")[2]))
check("LMS simulado: página y JWKS", lambda: "Aula virtual" in call("GET", LMS + "/")[2] and "keys" in json.loads(call("GET", LMS + "/jwks")[2]))

ctx = {}


def lti_login(role, user):
    st, h, _ = call("POST", LTI + "/lti/login/", form=True, data={"iss": LMS, "client_id": "mock-client", "lti_deployment_id": "mock-deployment-1",
                    "target_link_uri": LTI + "/lti/launch/", "lti_message_hint": role, "login_hint": user})
    assert st == 302, f"login devolvió {st}"
    st, _, page = call("GET", h["Location"])
    assert st == 200, f"LMS /auth devolvió {st}: {page[:80]}"
    fields = dict(re.findall(r'name="(id_token|state)" value="([^"]*)"', page))
    st, h, body = call("POST", LTI + "/lti/launch/", form=True, data=fields)
    assert st == 302, f"launch devolvió {st}: {body[:200]}"
    token = urllib.parse.parse_qs(urllib.parse.urlparse(h["Location"]).query)["token"][0]
    st, _, body = call("POST", API + "/v1/lti/exchange", data={"token": token})
    assert st == 200, f"exchange devolvió {st}: {body[:120]}"
    return {"Authorization": "Bearer " + json.loads(body)["access_token"]}


def lti_chain():
    ctx["bearer"] = lti_login("student", "alumno-smoke")


def start_practice():
    st, _, body = call("POST", API + "/v1/sessions", data={"mode": "practica"}, headers=ctx["bearer"])
    if st == 403 and "consentimiento" in body:                       # modo producción: el docente confirma el consentimiento
        teacher = lti_login("teacher", "docente-smoke")
        assert call("POST", API + "/v1/teacher/consent", headers=teacher)[0] == 200
        st, _, body = call("POST", API + "/v1/sessions", data={"mode": "practica"}, headers=ctx["bearer"])
    assert st == 200, f"start devolvió {st}: {body[:150]}"
    ctx["sid"], ctx["state"] = json.loads(body)["session_id"], json.loads(body)


def finish_practice():
    state, n = ctx["state"], 0
    while not state["done"]:
        item = state["items"][0]
        resp = "A" if item["kind"] == "choice" else ("n" if item["kind"] == "expression" else "1")
        st, _, body = call("POST", f"{API}/v1/sessions/{ctx['sid']}/answers", data={"item_id": item["id"], "response": resp}, headers=ctx["bearer"])
        assert st == 200, f"answer devolvió {st}: {body[:150]}"
        state, n = json.loads(body), n + 1
    return n == 24 or f"se respondieron {n} preguntas"


def gradebook_has_grade():
    import time
    for _ in range(20):                                            # la devolución de la nota corre en segundo plano
        if "alumno-smoke" in call("GET", LMS + "/gradebook")[2]:
            return True
        time.sleep(0.5)
    return "la nota no llegó al libro de calificaciones (revisá la ventana del servicio LTI y la de la API)"


check("LTI completo: LMS -> servicio LTI -> API (intercambio de token)", lti_chain)
check("LTI: el estudiante inicia una práctica con ese acceso", start_practice)
check("Práctica: responde las 24 preguntas", finish_practice)
check("Notas: la nota llegó al libro de calificaciones del LMS", gradebook_has_grade)


def observatory_ok():
    st, _, body = call("GET", API + "/v1/observatory/series?domain=matematica&entities=Argentina", headers=ctx["bearer"])
    assert st == 200, f"observatorio devolvió {st}: {body[:120]}"
    arg = json.loads(body)["series"][0]
    return arg["entity"] == "Argentina" and arg["points"][-1] == [2025, 367] or f"serie inesperada: {arg['points'][-2:]}"


check("Observatorio: serie histórica de Argentina con la fuente", observatory_ok)
check("Observatorio: endpoint de brechas responde", lambda: call("GET", API + "/v1/observatory/gaps?entity=Argentina&domain=matematica", headers=ctx["bearer"])[0] == 200)
for name, ok, err in results:
    print(("PASA  " if ok else "FALLA ") + name + (f"  -> {err}" if err else ""))
sys.exit(0 if all(ok for _, ok, _ in results) else 1)

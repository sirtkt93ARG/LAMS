def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)

# ---- almacén
patch("api/app/store.py", [
('''CREATE TABLE IF NOT EXISTS tenant_networks (
  network_id TEXT NOT NULL, tenant_id TEXT NOT NULL, PRIMARY KEY (network_id, tenant_id));''','''CREATE TABLE IF NOT EXISTS tenant_networks (
  network_id TEXT NOT NULL, tenant_id TEXT NOT NULL, accepted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (network_id, tenant_id));
CREATE TABLE IF NOT EXISTS used_tokens (jti TEXT PRIMARY KEY, used_at TEXT NOT NULL DEFAULT (datetime('now')));'''),
('''                       ("responses", "hints", "INTEGER NOT NULL DEFAULT 0")]''','''                       ("responses", "hints", "INTEGER NOT NULL DEFAULT 0"), ("tenant_networks", "accepted", "INTEGER NOT NULL DEFAULT 0")]'''),
('''                self._conn.commit()
        elif url.startswith(("postgresql://"''','''                try:                                                   # una respuesta por ejercicio y sesión
                    self._conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_responses_session_item ON responses (session_id, item_id)")
                except sqlite3.IntegrityError:
                    pass                                               # bases viejas con duplicados: limpiar a mano antes de crearlo
                self._conn.commit()
        elif url.startswith(("postgresql://"'''),
('''            return sql.replace("{J}", "?").replace("{NOW}", "datetime('now')")''','''            return sql.replace("{J}", "?").replace("{NOW}", "datetime('now')").replace("{HOUR_AGO}", "datetime('now', '-1 hour')")'''),
('''        return sql.replace("{J}", "%s::jsonb").replace("{NOW}", "now()").replace("?", "%s")''','''        return sql.replace("{J}", "%s::jsonb").replace("{NOW}", "now()").replace("{HOUR_AGO}", "now() - interval '1 hour'").replace("?", "%s")'''),
('''                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (tenant, sid, item_id, response, score, tag, duration_s, hints))''','''                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (session_id, item_id) DO NOTHING",
                  (tenant, sid, item_id, response, score, tag, duration_s, hints))'''),
('''    def add_network_tenant(self, network_id: str, tenant: str) -> None:
        if tenant not in self.network_tenants(network_id):
            self._run(None, "INSERT INTO tenant_networks (network_id, tenant_id) VALUES (?, ?)", (network_id, tenant))

    def network_tenants(self, network_id: str) -> list[str]:
        rows = self._run(None, "SELECT tenant_id FROM tenant_networks WHERE network_id = ? ORDER BY tenant_id", (network_id,), fetch=True)
        return [r["tenant_id"] for r in rows]''','''    def add_network_tenant(self, network_id: str, tenant: str) -> None:
        """Crea una invitación pendiente: la escuela debe aceptarla para que la red vea sus resultados agregados."""
        if tenant not in self.network_tenants(network_id, accepted_only=False):
            self._run(None, "INSERT INTO tenant_networks (network_id, tenant_id, accepted) VALUES (?, ?, 0)", (network_id, tenant))

    def network_tenants(self, network_id: str, accepted_only: bool = True) -> list[str]:
        rows = self._run(None, "SELECT tenant_id FROM tenant_networks WHERE network_id = ?" + (" AND accepted = 1" if accepted_only else "")
                         + " ORDER BY tenant_id", (network_id,), fetch=True)
        return [r["tenant_id"] for r in rows]

    def pending_invites(self, tenant: str) -> list[str]:
        rows = self._run(None, "SELECT network_id FROM tenant_networks WHERE tenant_id = ? AND accepted = 0 ORDER BY network_id", (tenant,), fetch=True)
        return [r["network_id"] for r in rows]

    def answer_invite(self, network_id: str, tenant: str, accept: bool) -> bool:
        if network_id not in self.pending_invites(tenant):
            return False
        if accept:
            self._run(None, "UPDATE tenant_networks SET accepted = 1 WHERE network_id = ? AND tenant_id = ?", (network_id, tenant))
        else:
            self._run(None, "DELETE FROM tenant_networks WHERE network_id = ? AND tenant_id = ? AND accepted = 0", (network_id, tenant))
        return True

    def consume_token(self, jti: str) -> bool:
        """Marca un token como usado. Devuelve False si ya se había usado (un token de traspaso vale una sola vez)."""
        self._run(None, "DELETE FROM used_tokens WHERE used_at < {HOUR_AGO}")
        try:
            self._run(None, "INSERT INTO used_tokens (jti) VALUES (?)", (jti,))
        except Exception:                                                        # noqa: BLE001 (clave primaria repetida)
            return False
        return True'''),
])
# ---- autenticación
patch("api/app/auth.py", [
('''_jwks = jwt.PyJWKClient(''','''_consume = None          # función que marca un token como usado (la fija main.py con el Store)


def set_token_consumer(fn) -> None:
    global _consume
    _consume = fn


_jwks = jwt.PyJWKClient('''),
('''    if c.get("role") not in ("student", "teacher", "admin"):
        raise HTTPException(403, "rol no permitido")''','''    if c.get("role") not in ("student", "teacher", "admin"):
        raise HTTPException(403, "rol no permitido")
    if not c.get("jti"):
        raise HTTPException(401, "token sin identificador")
    if _consume is not None and not _consume(c["jti"]):
        raise HTTPException(401, "el token ya fue utilizado")'''),
])
patch("lti_service/app.py", [
("import time\nimport jwt","import time\nimport uuid\nimport jwt"),
('''"tenant_id": tenant, "exp": int(time.time()) + 60}''','''"tenant_id": tenant, "jti": uuid.uuid4().hex, "exp": int(time.time()) + 60}'''),
])
# ---- API
patch("api/app/main.py", [
("from .auth import DEV, User, current_user, mint_session_token, verify_handoff","from .auth import DEV, User, current_user, mint_session_token, set_token_consumer, verify_handoff"),
("from .store import Store","from .security import check_config\nfrom .store import Store"),
('''SECRET = os.getenv("PSEUDONYM_SECRET", "cambiar-en-produccion").encode()''','''_errors, _warnings = check_config(os.environ, DEV)
for _w in _warnings:
    log.warning("configuración: %s", _w)
if _errors and os.getenv("ALLOW_INSECURE_CONFIG") != "1":
    raise RuntimeError("Configuración insegura: " + "; ".join(_errors) + " (ALLOW_INSECURE_CONFIG=1 solo para pruebas)")
set_token_consumer(STORE.consume_token)
SECRET = os.getenv("PSEUDONYM_SECRET", "cambiar-en-produccion").encode()'''),
("pool = [PoolItem(i.id, i.axis.value, _params(i, body.mode)) for i in _pool(body.mode)]","pool = [PoolItem(i.id, i.axis.value, _params(i, body.mode), i.provenance.get(\"fp\")) for i in _pool(body.mode)]"),
("        design = build_design(pool)\n        eng = MSTSession","        design = build_design(pool, rng=random.Random())\n        eng = MSTSession"),
('''@app.get("/v1/review/templates")
def review_templates''','''def _curator(user: User) -> None:
    """La revisión de plantillas cambia el banco de TODAS las escuelas: la hacen solo curadores del banco (rol admin)."""
    if user.role != "admin":
        raise HTTPException(403, "solo curadores del banco de ejercicios")


@app.get("/v1/review/templates")
def review_templates'''),
("def review_templates(user: User = Depends(current_user)):\n    _teacher(user)","def review_templates(user: User = Depends(current_user)):\n    _curator(user)"),
("def review_sample(tid: str, n: int = 5, user: User = Depends(current_user)):\n    _teacher(user)","def review_sample(tid: str, n: int = 5, user: User = Depends(current_user)):\n    _curator(user)"),
("def review_submit(tid: str, body: ReviewIn, user: User = Depends(current_user)):\n    _teacher(user)","def review_submit(tid: str, body: ReviewIn, user: User = Depends(current_user)):\n    _curator(user)"),
('''    _network(user)
    STORE.add_network_tenant(user.tenant_id, body.token)
    STORE.audit(user.tenant_id, user.sub, "escuela_agregada_a_la_red", body.token)
    return {"tenants": STORE.network_tenants(user.tenant_id)}''','''    _network(user)
    STORE.add_network_tenant(user.tenant_id, body.token)
    STORE.audit(user.tenant_id, user.sub, "invitacion_a_escuela", body.token)
    return {"tenants": STORE.network_tenants(user.tenant_id), "pending": STORE.network_tenants(user.tenant_id, accepted_only=False)}'''),
('"""Incorpora una escuela a la red. (Reutiliza el modelo con un solo campo de texto: el id de la escuela va en `token`.)"""','"""Invita a una escuela a la red (el id va en `token`). La red solo ve sus resultados cuando la escuela acepta la invitación."""'),
('''    return {"network_id": user.tenant_id, "min_cell": MIN_CELL, "schools": schools, "others": others_row,''','''    return {"network_id": user.tenant_id, "min_cell": MIN_CELL, "schools": schools, "others": others_row,
            "pending_invitations": len(STORE.network_tenants(user.tenant_id, accepted_only=False)) - len(STORE.network_tenants(user.tenant_id)),'''),
('''@app.get("/v1/teacher/consent")''','''@app.get("/v1/teacher/network-invites")
def network_invites(user: User = Depends(current_user)):
    """Redes que pidieron ver los resultados agregados de la escuela y esperan una respuesta."""
    _teacher(user)
    return {"invites": STORE.pending_invites(user.tenant_id)}


@app.post("/v1/teacher/network-invites/{network_id}/{decision}")
def network_invite_answer(network_id: str, decision: str, user: User = Depends(current_user)):
    _teacher(user)
    if decision not in ("accept", "decline"):
        raise HTTPException(400, "la decisión debe ser accept o decline")
    if not STORE.answer_invite(network_id, user.tenant_id, decision == "accept"):
        raise HTTPException(404, "invitación no encontrada")
    STORE.audit(user.tenant_id, user.sub, f"invitacion_{decision}", network_id)
    return {"invites": STORE.pending_invites(user.tenant_id)}


@app.get("/v1/teacher/consent")'''),
])
# ---- PostgreSQL
s = open("db/001_init.sql", encoding="utf-8").read()
s = s.replace("CREATE INDEX ix_responses_session ON responses (tenant_id, session_id);", "CREATE INDEX ix_responses_session ON responses (tenant_id, session_id);\nCREATE UNIQUE INDEX ux_responses_session_item ON responses (session_id, item_id);")
assert "tenant_networks" not in s
s = s.replace("-- Revisiones docentes", """CREATE TABLE tenant_networks (
  network_id text NOT NULL, tenant_id text NOT NULL, accepted integer NOT NULL DEFAULT 0, PRIMARY KEY (network_id, tenant_id));

CREATE TABLE used_tokens (jti text PRIMARY KEY, used_at timestamptz NOT NULL DEFAULT now());

-- Revisiones docentes""", 1)
s = s.replace("GRANT SELECT, INSERT ON item_reviews, audit_log TO matheval_app;", "GRANT SELECT, INSERT ON item_reviews, audit_log TO matheval_app;\nGRANT SELECT, INSERT, UPDATE, DELETE ON tenant_networks, used_tokens TO matheval_app;")
open("db/001_init.sql", "w", encoding="utf-8").write(s)
open("db/003_migracion_v08.sql", "w", encoding="utf-8").write("""-- Migración para bases PostgreSQL creadas con la versión 0.5 a 0.7 (NO PROBADA). Ejecutar con el rol propietario.
-- 1) Una sola respuesta por ejercicio y sesión (antes puede haber duplicados por solicitudes simultáneas): se conserva la primera.
DELETE FROM responses a USING responses b WHERE a.session_id = b.session_id AND a.item_id = b.item_id AND a.id > b.id;
CREATE UNIQUE INDEX IF NOT EXISTS ux_responses_session_item ON responses (session_id, item_id);
-- 2) Invitaciones de red: las existentes quedan como pendientes hasta que cada escuela las acepte.
CREATE TABLE IF NOT EXISTS tenant_networks (network_id text NOT NULL, tenant_id text NOT NULL, accepted integer NOT NULL DEFAULT 0, PRIMARY KEY (network_id, tenant_id));
ALTER TABLE tenant_networks ADD COLUMN IF NOT EXISTS accepted integer NOT NULL DEFAULT 0;
-- 3) Tokens de traspaso de un solo uso.
CREATE TABLE IF NOT EXISTS used_tokens (jti text PRIMARY KEY, used_at timestamptz NOT NULL DEFAULT now());
GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_networks, used_tokens TO matheval_app;
""")
# ---- scripts de arranque
patch("scripts/dev.ps1", [('$env:LTI_SECRET_KEY = "dev-flask-secret"','$env:LTI_SECRET_KEY = "dev-flask-secret"\n$env:PSEUDONYM_SECRET = "dev-pseudonym-secret-cambiar-0123456789abcdef"')])
patch("scripts/dev.sh", [("LTI_SECRET_KEY=dev-flask-secret","LTI_SECRET_KEY=dev-flask-secret PSEUDONYM_SECRET=dev-pseudonym-secret-cambiar-0123456789abcdef")])

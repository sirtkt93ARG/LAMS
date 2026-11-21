"""Persistencia de sesiones, respuestas, revisiones, consentimiento y auditoría. Un mismo código para SQLite
(desarrollo y pruebas) y PostgreSQL (producción, con seguridad a nivel de fila: ver db/001_init.sql).

Privacidad: solo se guarda el identificador seudónimo (`pid`), nunca el identificador real del usuario.
Defensa en profundidad: toda consulta por escuela filtra por tenant_id además de la política RLS."""
from __future__ import annotations
import json
import sqlite3
import threading
from datetime import datetime, timezone

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, pid TEXT NOT NULL, mode TEXT NOT NULL,
  state TEXT NOT NULL, result TEXT, started_at TEXT NOT NULL DEFAULT (datetime('now')), finished_at TEXT,
  course_id TEXT, course_label TEXT);
CREATE INDEX IF NOT EXISTS ix_sessions_tenant ON sessions (tenant_id);
CREATE TABLE IF NOT EXISTS responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, session_id TEXT NOT NULL, item_id TEXT NOT NULL,
  response TEXT, score REAL, error_tag TEXT, duration_s REAL, answered_at TEXT NOT NULL DEFAULT (datetime('now')),
  hints INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_responses_session ON responses (tenant_id, session_id);
CREATE TABLE IF NOT EXISTS item_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL,
  comment TEXT, checklist TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')), UNIQUE (scope, reviewer));
CREATE TABLE IF NOT EXISTS tenant_settings (
  tenant_id TEXT PRIMARY KEY, consent_attested_at TEXT, consent_attested_by TEXT, retention_days INTEGER NOT NULL DEFAULT 365);
CREATE TABLE IF NOT EXISTS tenant_networks (
  network_id TEXT NOT NULL, tenant_id TEXT NOT NULL, accepted INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (network_id, tenant_id));
CREATE TABLE IF NOT EXISTS used_tokens (
  jti TEXT PRIMARY KEY, used_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL DEFAULT (datetime('now')), tenant_id TEXT, actor TEXT NOT NULL,
  action TEXT NOT NULL, detail TEXT);
"""
_SQLITE_NEW_COLUMNS = [("sessions", "course_id", "TEXT"), ("sessions", "course_label", "TEXT"),
                       ("responses", "hints", "INTEGER NOT NULL DEFAULT 0"),
                       ("tenant_networks", "accepted", "INTEGER NOT NULL DEFAULT 0")]


def _loads(x):
    return json.loads(x) if isinstance(x, (str, bytes)) else x


def _ts(x):
    if x is None or isinstance(x, datetime):
        return x
    return datetime.fromisoformat(str(x).replace(" ", "T")).replace(tzinfo=timezone.utc)


class Store:
    def __init__(self, url: str):
        self.url = url
        if url.startswith("sqlite:///"):
            self.dialect = "sqlite"
            self._conn = sqlite3.connect(url[len("sqlite:///"):], check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._lock = threading.Lock()
            with self._lock:
                self._conn.executescript(_SQLITE_DDL)
                for table, col, decl in _SQLITE_NEW_COLUMNS:         # migra bases creadas con versiones anteriores
                    cols = {r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})")}
                    if col not in cols:
                        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                self._conn.commit()
        elif url.startswith(("postgresql://", "postgres://")):
            self.dialect = "pg"      # el esquema lo crea db/001_init.sql (o db/002_migracion_v05.sql si ya existía)
        else:
            raise ValueError("DATABASE_URL debe empezar con sqlite:/// o postgresql://")

    def _sql(self, sql: str) -> str:
        if self.dialect == "sqlite":
            return sql.replace("{J}", "?").replace("{NOW}", "datetime('now')")
        return sql.replace("{J}", "%s::jsonb").replace("{NOW}", "now()").replace("?", "%s")

    def _run(self, tenant: str | None, sql: str, params: tuple = (), fetch: bool = False) -> list[dict]:
        sql = self._sql(sql)
        if self.dialect == "sqlite":
            with self._lock:
                cur = self._conn.execute(sql, params)
                rows = [dict(r) for r in cur.fetchall()] if fetch else []
                self._conn.commit()
                return rows
        import psycopg                                   # carga diferida: solo hace falta con PostgreSQL
        from psycopg.rows import dict_row
        with psycopg.connect(self.url, row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant or "",))
                cur = conn.execute(sql, params)
                return list(cur.fetchall()) if fetch else []

    # ---- sesiones -----------------------------------------------------------------
    def create_session(self, sid: str, tenant: str, pid: str, mode: str, state: dict,
                       course_id: str | None = None, course_label: str | None = None) -> None:
        self._run(tenant, "INSERT INTO sessions (id, tenant_id, pid, mode, state, course_id, course_label) VALUES (?, ?, ?, ?, {J}, ?, ?)",
                  (sid, tenant, pid, mode, json.dumps(state), course_id, course_label))

    def load_session(self, sid: str, tenant: str) -> dict | None:
        rows = self._run(tenant, "SELECT id, pid, mode, state, result, finished_at, course_id, course_label FROM sessions "
                                 "WHERE id = ? AND tenant_id = ?", (sid, tenant), fetch=True)
        if not rows:
            return None
        r = rows[0]
        return {**{k: r[k] for k in ("id", "pid", "mode", "finished_at", "course_id", "course_label")},
                "state": _loads(r["state"]), "result": _loads(r["result"]) if r["result"] else None}

    def save_session(self, sid: str, tenant: str, state: dict, result: dict | None = None) -> None:
        if result is None:
            self._run(tenant, "UPDATE sessions SET state = {J} WHERE id = ? AND tenant_id = ?", (json.dumps(state), sid, tenant))
        else:
            self._run(tenant, "UPDATE sessions SET state = {J}, result = {J}, finished_at = {NOW} WHERE id = ? AND tenant_id = ?",
                      (json.dumps(state), json.dumps(result), sid, tenant))

    def add_response(self, tenant: str, sid: str, item_id: str, response: str, score: float | None,
                     tag: str | None, duration_s: float | None, hints: int = 0) -> None:
        self._run(tenant, "INSERT INTO responses (tenant_id, session_id, item_id, response, score, error_tag, duration_s, hints) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (tenant, sid, item_id, response, score, tag, duration_s, hints))

    def sessions_of(self, tenant: str, pid: str, limit: int = 30) -> list[dict]:
        rows = self._run(tenant, "SELECT id, mode, result, started_at, finished_at FROM sessions WHERE tenant_id = ? AND pid = ? "
                                 "ORDER BY started_at DESC LIMIT " + str(int(limit)), (tenant, pid), fetch=True)
        return [{**r, "result": _loads(r["result"]) if r["result"] else None} for r in rows]

    def responses_for_pid(self, tenant: str, pid: str) -> list[tuple]:
        rows = self._run(tenant, "SELECT r.item_id, r.score, r.answered_at, r.hints FROM responses r JOIN sessions s "
                                 "ON s.id = r.session_id AND s.tenant_id = r.tenant_id WHERE r.tenant_id = ? AND s.pid = ? ORDER BY r.id",
                         (tenant, pid), fetch=True)
        return [(r["item_id"], r["score"], _ts(r["answered_at"]), r["hints"]) for r in rows]

    def tenant_rows(self, tenant: str | None, course: str | None = None) -> list[dict]:
        """Respuestas con seudónimo. tenant=None: todas las escuelas (solo tareas de administración con el rol propietario)."""
        q = ("SELECT s.pid, s.tenant_id, s.course_id, r.item_id, r.score, r.response, r.duration_s, r.hints, r.answered_at "
             "FROM responses r JOIN sessions s ON s.id = r.session_id AND s.tenant_id = r.tenant_id")
        conds, params = [], []
        if tenant is not None:
            conds.append("r.tenant_id = ?"); params.append(tenant)
        if course:
            conds.append("s.course_id = ?"); params.append(course)
        rows = self._run(tenant, q + (" WHERE " + " AND ".join(conds) if conds else "") + " ORDER BY r.id", tuple(params), fetch=True)
        return [{**r, "answered_at": _ts(r["answered_at"])} for r in rows]

    def finished_results(self, tenant: str, course: str | None = None) -> list[dict]:
        q = "SELECT result FROM sessions WHERE tenant_id = ? AND result IS NOT NULL AND mode IN ('practica', 'medicion')"
        rows = self._run(tenant, q + (" AND course_id = ?" if course else ""), (tenant, course) if course else (tenant,), fetch=True)
        return [_loads(r["result"]) for r in rows]

    def finished_dated(self, tenant: str, course: str | None = None) -> list[dict]:
        """Resultados terminados con su fecha, para ver tendencias en el tiempo."""
        q = ("SELECT finished_at, result FROM sessions WHERE tenant_id = ? AND result IS NOT NULL AND finished_at IS NOT NULL "
             "AND mode IN ('practica', 'medicion')" + (" AND course_id = ?" if course else "") + " ORDER BY finished_at")
        rows = self._run(tenant, q, (tenant, course) if course else (tenant,), fetch=True)
        return [{"at": _ts(r["finished_at"]), **_loads(r["result"])} for r in rows]

    def add_network_tenant(self, network_id: str, tenant: str) -> None:
        """Crea una invitación pendiente; la escuela decide si comparte sus agregados."""
        self._run(None, "INSERT INTO tenant_networks (network_id, tenant_id, accepted) VALUES (?, ?, FALSE) "
                        "ON CONFLICT (network_id, tenant_id) DO NOTHING", (network_id, tenant), tenant=network_id)

    def network_tenants(self, network_id: str, accepted_only: bool = True) -> list[str]:
        q = "SELECT tenant_id FROM tenant_networks WHERE network_id = ?" + (" AND accepted = TRUE" if accepted_only else "")
        rows = self._run(network_id, q + " ORDER BY tenant_id", (network_id,), fetch=True)
        return [r["tenant_id"] for r in rows]

    def pending_network_tenants(self, network_id: str) -> list[str]:
        rows = self._run(network_id, "SELECT tenant_id FROM tenant_networks WHERE network_id = ? AND accepted = FALSE ORDER BY tenant_id",
                         (network_id,), fetch=True)
        return [r["tenant_id"] for r in rows]

    def pending_invites(self, tenant: str) -> list[str]:
        rows = self._run(tenant, "SELECT network_id FROM tenant_networks WHERE tenant_id = ? AND accepted = FALSE ORDER BY network_id",
                         (tenant,), fetch=True)
        return [r["network_id"] for r in rows]

    def answer_invite(self, network_id: str, tenant: str, accept: bool) -> bool:
        """Acepta o rechaza una invitación pendiente de forma atómica."""
        if self.dialect == "sqlite":
            with self._lock:
                if accept:
                    cur = self._conn.execute(
                        "UPDATE tenant_networks SET accepted = 1 WHERE network_id = ? AND tenant_id = ? AND accepted = 0",
                        (network_id, tenant))
                else:
                    cur = self._conn.execute(
                        "DELETE FROM tenant_networks WHERE network_id = ? AND tenant_id = ? AND accepted = 0",
                        (network_id, tenant))
                self._conn.commit()
                return cur.rowcount == 1
        import psycopg
        with psycopg.connect(self.url) as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
                if accept:
                    cur = conn.execute(
                        "UPDATE tenant_networks SET accepted = TRUE WHERE network_id = %s AND tenant_id = %s AND accepted = FALSE RETURNING tenant_id",
                        (network_id, tenant))
                else:
                    cur = conn.execute(
                        "DELETE FROM tenant_networks WHERE network_id = %s AND tenant_id = %s AND accepted = FALSE RETURNING tenant_id",
                        (network_id, tenant))
                return cur.fetchone() is not None

    def consume_token(self, jti: str) -> bool:
        """Consume an LTI handoff JTI atomically; a token can be exchanged only once."""
        if not jti:
            return False
        if self.dialect == "sqlite":
            with self._lock:
                self._conn.execute("DELETE FROM used_tokens WHERE used_at < datetime('now', '-1 hour')")
                cur = self._conn.execute(
                    "INSERT INTO used_tokens (jti) VALUES (?) ON CONFLICT(jti) DO NOTHING", (jti,))
                self._conn.commit()
                return cur.rowcount == 1
        import psycopg
        with psycopg.connect(self.url) as conn:
            with conn.transaction():
                conn.execute("DELETE FROM used_tokens WHERE used_at < now() - interval '1 hour'")
                cur = conn.execute(
                    "INSERT INTO used_tokens (jti) VALUES (%s) ON CONFLICT (jti) DO NOTHING RETURNING jti", (jti,))
                return cur.fetchone() is not None

    def courses(self, tenant: str) -> list[dict]:
        return self._run(tenant, "SELECT course_id, MAX(course_label) AS course_label, COUNT(*) AS sessions FROM sessions "
                                 "WHERE tenant_id = ? AND course_id IS NOT NULL GROUP BY course_id ORDER BY course_id", (tenant,), fetch=True)

    def error_counts(self, tenant: str, course: str | None = None) -> dict[str, int]:
        q = ("SELECT r.error_tag AS tag, COUNT(*) AS n FROM responses r JOIN sessions s ON s.id = r.session_id AND s.tenant_id = r.tenant_id "
             "WHERE r.tenant_id = ? AND r.error_tag IS NOT NULL" + (" AND s.course_id = ?" if course else "") +
             " GROUP BY r.error_tag ORDER BY n DESC")
        rows = self._run(tenant, q, (tenant, course) if course else (tenant,), fetch=True)
        return {r["tag"]: r["n"] for r in rows}

    # ---- derechos de los datos --------------------------------------------------------
    def delete_learner(self, tenant: str, pid: str) -> dict:
        n_s = self._run(tenant, "SELECT COUNT(*) AS n FROM sessions WHERE tenant_id = ? AND pid = ?", (tenant, pid), fetch=True)[0]["n"]
        n_r = self._run(tenant, "SELECT COUNT(*) AS n FROM responses WHERE tenant_id = ? AND session_id IN "
                                "(SELECT id FROM sessions WHERE tenant_id = ? AND pid = ?)", (tenant, tenant, pid), fetch=True)[0]["n"]
        self._run(tenant, "DELETE FROM responses WHERE tenant_id = ? AND session_id IN (SELECT id FROM sessions WHERE tenant_id = ? AND pid = ?)",
                  (tenant, tenant, pid))
        self._run(tenant, "DELETE FROM sessions WHERE tenant_id = ? AND pid = ?", (tenant, pid))
        return {"sessions": n_s, "responses": n_r}

    def purge_older_than(self, days: int) -> int:
        """Borra sesiones y respuestas más viejas que `days` días, de todas las escuelas (rol propietario)."""
        if self.dialect == "sqlite":
            cond, p = "started_at < datetime('now', ?)", (f"-{int(days)} days",)
        else:
            cond, p = "started_at < now() - make_interval(days => ?)", (int(days),)
        n = self._run(None, f"SELECT COUNT(*) AS n FROM sessions WHERE {cond}", p, fetch=True)[0]["n"]
        self._run(None, f"DELETE FROM responses WHERE session_id IN (SELECT id FROM sessions WHERE {cond})", p)
        self._run(None, f"DELETE FROM sessions WHERE {cond}", p)
        return n

    # ---- escuela: consentimiento y auditoría -------------------------------------------
    def tenant_settings(self, tenant: str) -> dict:
        rows = self._run(tenant, "SELECT consent_attested_at, consent_attested_by, retention_days FROM tenant_settings WHERE tenant_id = ?",
                         (tenant,), fetch=True)
        return rows[0] if rows else {"consent_attested_at": None, "consent_attested_by": None, "retention_days": 365}

    def attest_consent(self, tenant: str, by: str) -> None:
        self._run(tenant, "INSERT INTO tenant_settings (tenant_id, consent_attested_at, consent_attested_by) VALUES (?, {NOW}, ?) "
                          "ON CONFLICT (tenant_id) DO UPDATE SET consent_attested_at = {NOW}, consent_attested_by = excluded.consent_attested_by",
                  (tenant, by))

    def audit(self, tenant: str | None, actor: str, action: str, detail: str = "") -> None:
        self._run(tenant, "INSERT INTO audit_log (tenant_id, actor, action, detail) VALUES (?, ?, ?, ?)", (tenant, actor, action, detail))

    def audit_list(self, tenant: str, limit: int = 100) -> list[dict]:
        return self._run(tenant, "SELECT at, actor, action, detail FROM audit_log WHERE tenant_id = ? ORDER BY id DESC LIMIT " + str(int(limit)),
                         (tenant,), fetch=True)

    # ---- revisiones (no dependen de la escuela) -----------------------------------------
    def add_review(self, scope: str, reviewer: str, decision: str, comment: str, checklist: dict) -> None:
        self._run(None, "INSERT INTO item_reviews (scope, reviewer, decision, comment, checklist) VALUES (?, ?, ?, ?, {J})",
                  (scope, reviewer, decision, comment, json.dumps(checklist)))

    def reviews(self, scope: str | None = None) -> list[dict]:
        q = "SELECT scope, reviewer, decision, comment, checklist, created_at FROM item_reviews"
        rows = self._run(None, q + (" WHERE scope = ?" if scope else "") + " ORDER BY id", (scope,) if scope else (), fetch=True)
        return [{**r, "checklist": _loads(r["checklist"]) if r["checklist"] else {}} for r in rows]

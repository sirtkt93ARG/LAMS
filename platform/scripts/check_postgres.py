"""Verifica el esquema PostgreSQL y el aislamiento por escuela (RLS) contra una base real.
Uso: python scripts/check_postgres.py --admin-url postgresql://postgres:cambiar@localhost:5432/matheval
                                     --app-url postgresql://matheval_app:cambiar-en-produccion@localhost:5432/matheval
ATENCIÓN: borra y recrea las tablas sessions, responses e item_reviews de esa base."""
import argparse, pathlib, sys, uuid
sys.path.insert(0, "."); sys.path.insert(0, "api/..")
import psycopg
from api.app.store import Store

ap = argparse.ArgumentParser()
ap.add_argument("--admin-url", required=True)
ap.add_argument("--app-url", required=True)
a = ap.parse_args()
results = []


def check(name, fn):
    try:
        ok = fn()
        results.append((name, ok is not False, ""))
    except Exception as e:                       # noqa: BLE001
        results.append((name, False, repr(e)[:160]))


with psycopg.connect(a.admin_url, autocommit=True) as c:
    c.execute("DROP TABLE IF EXISTS responses, sessions, item_reviews, tenant_settings, audit_log CASCADE")
    c.execute(pathlib.Path("db/001_init.sql").read_text(encoding="utf-8"))
print("Esquema aplicado.")

st = Store(a.app_url)
sa, sb = str(uuid.uuid4()), str(uuid.uuid4())


def t_roundtrip():
    st.create_session(sa, "escuela-A", "pidA", "practica", {"x": 1})
    st.save_session(sa, "escuela-A", {"x": 2}, {"level": 4, "theta": 0.1, "se": 0.3})
    row = st.load_session(sa, "escuela-A")
    assert row["state"] == {"x": 2} and row["result"]["level"] == 4 and row["finished_at"]
    st.add_response("escuela-A", sa, "T1-1", "A", 1.0, None, 3.2)


def t_isolation_app():
    st.create_session(sb, "escuela-B", "pidB", "practica", {"y": 1})
    assert st.load_session(sb, "escuela-A") is None
    assert [r["level"] for r in st.finished_results("escuela-A")] == [4]
    assert st.finished_results("escuela-B") == []


def _count(tenant):
    with psycopg.connect(a.app_url) as c:
        with c.transaction():
            if tenant is not None:
                c.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
            return c.execute("SELECT count(*) FROM sessions").fetchone()[0]


def t_rls_raw():                                  # sin el WHERE de la aplicación: lo filtra la base
    assert _count("escuela-A") == 1 and _count("escuela-B") == 1 and _count(None) == 0


def t_rls_with_check():
    with psycopg.connect(a.app_url) as c:
        with c.transaction():
            c.execute("SELECT set_config('app.tenant_id', 'escuela-A', true)")
            try:
                c.execute("INSERT INTO sessions (id, tenant_id, pid, mode, state) VALUES (%s, 'escuela-B', 'x', 'practica', '{}'::jsonb)",
                          (str(uuid.uuid4()),))
            except psycopg.Error:
                return True
    return False


def t_no_bypass():
    with psycopg.connect(a.admin_url) as c:
        return c.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'matheval_app'").fetchone()[0] is False


def t_reviews():
    st.add_review("template:T1", "docente-1", "aprobar", "", {"clave_correcta": True})
    assert len(st.reviews("template:T1")) == 1
    try:
        st.add_review("template:T1", "docente-1", "aprobar", "", {})
    except Exception:                             # noqa: BLE001
        return True
    return False


def t_new_tables():
    st.attest_consent("escuela-A", "docente-1")
    assert st.tenant_settings("escuela-A")["consent_attested_at"]
    assert st.tenant_settings("escuela-B")["consent_attested_at"] is None            # RLS en tenant_settings
    st.audit("escuela-A", "docente-1", "prueba", "ok")
    assert len(st.audit_list("escuela-A")) == 1 and st.audit_list("escuela-B") == []
    st.create_session(str(uuid.uuid4()), "escuela-A", "pidA", "dirigida", {}, "4A", "4.º A")
    assert [c["course_id"] for c in st.courses("escuela-A")] == ["4A"]
    assert len(st.tenant_rows("escuela-A")) == 1 and st.responses_for_pid("escuela-A", "pidA")[0][0] == "T1-1"
    assert st.delete_learner("escuela-A", "pidA")["sessions"] == 2


for name, fn in [("Crear, guardar y leer una sesión", t_roundtrip), ("Aislamiento entre escuelas (aplicación)", t_isolation_app),
                 ("RLS: la base filtra sin ayuda de la aplicación", t_rls_raw), ("RLS: rechaza insertar en otra escuela", t_rls_with_check),
                 ("El rol de la aplicación no puede saltear RLS", t_no_bypass), ("Revisiones: un voto por revisor", t_reviews),
                 ("Consentimiento, auditoría, cursos, respuestas y borrado", t_new_tables)]:
    check(name, fn)
for name, ok, err in results:
    print(("PASA  " if ok else "FALLA ") + name + (f"  -> {err}" if err else ""))
sys.exit(0 if all(ok for _, ok, _ in results) else 1)

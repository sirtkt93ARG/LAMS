import os, sys, tempfile, unittest
sys.path.insert(0, os.getcwd())
from matheval.adaptive import MSTSession, PoolItem, build_design
from matheval.models import IRTParams, Status
from matheval.bank import ItemBank
from matheval import templates as T
from api.app.store import Store
from api.app import review as R


def _pool(n=120):
    axes = ["numeros_algebra", "funciones_relaciones", "geometria_medida", "datos_azar"]
    return [PoolItem(f"i{k}", axes[k % 4], IRTParams(1.0, -2.5 + 5 * k / n, 0.0)) for k in range(n)]


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(f"sqlite:///{self.tmp.name}/t.db")

    def tearDown(self):
        self.store._conn.close()
        self.tmp.cleanup()

    def test_mst_snapshot_roundtrip(self):
        pool = _pool()
        d = build_design(pool)
        params = {p.id: p.params for p in pool}
        s = MSTSession(d, params)
        for k in range(11):                                  # a mitad de la etapa 2
            s.record(s.next_items()[0], k % 2)
        s2 = MSTSession.from_snapshot(self.roundtrip(s.snapshot()))
        self.assertEqual(s2.next_items(), s.next_items())
        self.assertEqual(s2.route, s.route)
        self.assertAlmostEqual(s2.estimate()[0], s.estimate()[0], places=9)

    def roundtrip(self, snap):
        self.store.create_session("s1", "esc", "pid1", "practica", {"snap": snap})
        return self.store.load_session("s1", "esc")["state"]["snap"]

    def test_isolation_between_tenants_and_results(self):
        self.store.create_session("s1", "esc-1", "p", "practica", {"x": 1})
        self.assertIsNone(self.store.load_session("s1", "esc-2"))
        self.store.save_session("s1", "esc-1", {"x": 2}, {"level": 4, "theta": 0.1, "se": 0.3})
        self.assertEqual(self.store.finished_results("esc-1")[0]["level"], 4)
        self.assertEqual(self.store.finished_results("esc-2"), [])
        self.assertEqual(self.store.load_session("s1", "esc-1")["state"], {"x": 2})
        self.store.add_response("esc-1", "s1", "T1-1", "A", 1.0, None, 3.5)

    def test_review_flow_promotes_and_rejects(self):
        bank = ItemBank([T.generate("T1", i) for i in range(5)] + [T.generate("T2", i) for i in range(5)])
        R.apply_reviews(bank, self.store)
        self.assertTrue(all(i.status == Status.VERIFICADO for i in bank.items.values()))
        self.store.add_review("template:T1", "docente-1", "aprobar", "", {k: True for k in R.CHECKLIST})
        R.apply_reviews(bank, self.store)
        t1 = [i for i in bank.items.values() if i.template == "T1"]
        self.assertTrue(all(i.status == Status.REVISADO and i.provenance["reviewed_by"] == "docente-1" for i in t1))
        self.assertEqual(len(bank.pool("practica")), 5)
        self.store.add_review("template:T2", "docente-1", "rechazar", "El gráfico no se entiende", {})
        R.apply_reviews(bank, self.store)
        self.assertTrue(all(i.status == Status.RECHAZADO for i in bank.items.values() if i.template == "T2"))
        self.assertEqual(len(bank.pool("practica")), 5)
        R.apply_reviews(bank, self.store)                       # idempotente
        self.assertEqual(len(bank.pool("practica")), 5)
        with self.assertRaises(Exception):                       # un revisor no vota dos veces
            self.store.add_review("template:T1", "docente-1", "aprobar", "", {})

    def test_template_status_needs_required_approvals(self):
        old = R.REQUIRED
        R.REQUIRED = 2
        try:
            one = [{"decision": "aprobar"}]
            self.assertEqual(R.template_status(one)["status"], "pendiente")
            self.assertEqual(R.template_status(one * 2)["status"], "aprobada")
            self.assertEqual(R.template_status(one * 2 + [{"decision": "rechazar"}])["status"], "rechazada")
        finally:
            R.REQUIRED = old


if __name__ == "__main__":
    unittest.main()


class TestStoreV05(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.st = Store(f"sqlite:///{self.tmp.name}/v5.db")

    def tearDown(self):
        self.st._conn.close(); self.tmp.cleanup()

    def _mk(self, sid, tenant, pid, course=None, mode="practica", level=None):
        self.st.create_session(sid, tenant, pid, mode, {"x": 1}, course, course and f"Curso {course}")
        self.st.add_response(tenant, sid, "T1-1", "A", 0.0, "suma_en_lugar_de_restar", 4.0)
        self.st.add_response(tenant, sid, "T7-2", "B", 1.0, None, 3.0, hints=1)
        if level:
            self.st.save_session(sid, tenant, {"x": 2}, {"level": level, "theta": 0.0, "se": 0.3})

    def test_courses_errors_rows_and_progress(self):
        self._mk("a", "e1", "p1", "4A", level=3); self._mk("b", "e1", "p2", "4B", level=5); self._mk("c", "e1", "p3", "4A", mode="dirigida", level=6)
        self.assertEqual([c["course_id"] for c in self.st.courses("e1")], ["4A", "4B"])
        self.assertEqual(sorted(r["level"] for r in self.st.finished_results("e1")), [3, 5])          # dirigida no cuenta
        self.assertEqual([r["level"] for r in self.st.finished_results("e1", "4A")], [3])
        self.assertEqual(self.st.error_counts("e1", "4A"), {"suma_en_lugar_de_restar": 2})
        rows = self.st.tenant_rows("e1", "4B")
        self.assertEqual({r["pid"] for r in rows}, {"p2"})
        self.assertEqual(rows[1]["hints"], 1)
        self.assertEqual(self.st.responses_for_pid("e1", "p1")[0][0], "T1-1")
        self.assertEqual(len(self.st.sessions_of("e1", "p1")), 1)
        self.assertEqual(len(self.st.tenant_rows(None)), 6)

    def test_delete_and_purge(self):
        self._mk("a", "e1", "p1"); self._mk("b", "e1", "p2"); self._mk("c", "e2", "p1")
        self.assertEqual(self.st.delete_learner("e1", "p1"), {"sessions": 1, "responses": 2})
        self.assertIsNone(self.st.load_session("a", "e1"))
        self.assertIsNotNone(self.st.load_session("b", "e1"))
        self.assertIsNotNone(self.st.load_session("c", "e2"))                  # otra escuela intacta
        self.st._run(None, "UPDATE sessions SET started_at = datetime('now', '-400 days') WHERE id = 'b'")
        self.assertEqual(self.st.purge_older_than(365), 1)
        self.assertEqual(len(self.st.tenant_rows("e1")), 0)

    def test_consent_audit_and_migration_of_old_database(self):
        self.assertIsNone(self.st.tenant_settings("e1")["consent_attested_at"])
        self.st.attest_consent("e1", "docente-1"); self.st.attest_consent("e1", "docente-2")
        s = self.st.tenant_settings("e1")
        self.assertTrue(s["consent_attested_at"])
        self.assertEqual(s["consent_attested_by"], "docente-2")
        self.st.audit("e1", "docente-2", "consent", "ok")
        self.assertEqual(self.st.audit_list("e1")[0]["action"], "consent")
        import sqlite3
        old = f"{self.tmp.name}/old.db"
        c = sqlite3.connect(old)
        c.executescript("CREATE TABLE sessions (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, pid TEXT NOT NULL, mode TEXT NOT NULL, state TEXT NOT NULL, result TEXT, started_at TEXT NOT NULL DEFAULT (datetime('now')), finished_at TEXT);"
                        "CREATE TABLE responses (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, session_id TEXT NOT NULL, item_id TEXT NOT NULL, response TEXT, score REAL, error_tag TEXT, duration_s REAL, answered_at TEXT NOT NULL DEFAULT (datetime('now')));")
        c.execute("INSERT INTO sessions (id, tenant_id, pid, mode, state) VALUES ('o','e','p','practica','{}')"); c.commit(); c.close()
        migrated = Store(f"sqlite:///{old}")                                    # no debe fallar y conserva los datos
        self.assertEqual(migrated.load_session("o", "e")["course_id"], None)
        migrated.add_response("e", "o", "T1-1", "A", 1.0, None, 1.0, hints=0)
        migrated._conn.close()

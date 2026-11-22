import os, sys, sqlite3, tempfile, unittest, threading, hashlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.getcwd())
from matheval.adaptive import MSTSession, PoolItem, build_design
from matheval.models import IRTParams, Status
from matheval.bank import ItemBank
from matheval import templates as T
from api.app.store import Store
from api.app.limits import RateLimiter
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


    def test_rate_limit_is_shared_across_store_instances_and_resets_by_window(self):
        other = Store(f"sqlite:///{self.tmp.name}/t.db")
        now = [120.0]
        try:
            first, second = RateLimiter(self.store, lambda: now[0]), RateLimiter(other, lambda: now[0])
            self.assertTrue(first.allow("hint:school:student", 3, 60))
            self.assertTrue(first.allow("hint:school:student", 3, 60))
            self.assertTrue(second.allow("hint:school:student", 3, 60))
            self.assertFalse(second.allow("hint:school:student", 3, 60))
            self.assertTrue(second.allow("hint:other:student", 3, 60))
            now[0] = 180.0
            self.assertTrue(second.allow("hint:school:student", 3, 60))
        finally:
            other._conn.close()

    def test_learner_erasure_deletes_open_submissions(self):
        self.store.create_open_assignment("oa-erase", "school-erase", None, "open-1", "Actividad", "", "teacher", None)
        self.store.submit_open_response("sub-erase", "oa-erase", "school-erase", "pid-erase", "respuesta privada")
        self.store.delete_learner("school-erase", "pid-erase")
        self.assertIsNone(self.store.open_submission_for_student("school-erase", "sub-erase", "pid-erase"))
        self.assertEqual(self.store.open_assignments_for_teacher("school-erase")[0]["submissions"], 0)

    def test_open_assignment_deadline_blocks_submission_atomically(self):
        self.store.create_open_assignment("oa-expired", "school-deadline", None, "open-1",
                                          "Actividad vencida", "", "teacher", "2000-01-01T00:00:00+00:00")
        self.assertTrue(self.store.open_assignment_expired("school-deadline", "oa-expired"))
        self.assertFalse(self.store.submit_open_response("sub-expired", "oa-expired", "school-deadline",
                                                         "pid-deadline", "Respuesta tardía"))
        self.assertEqual(self.store.open_submissions_for_assignment("school-deadline", "oa-expired"), [])

    def test_open_assignment_persists_competency_rubric_snapshot(self):
        snapshot = {
            "version": 1, "competency_id": "porcentajes", "competency": "Porcentajes",
            "criteria": [{"id": "interpretacion", "label": "Interpretación",
                          "descriptors": {"0": "Sin evidencia"}}],
        }
        self.store.create_open_assignment("oa-rubric", "school-rubric", None, "open-1",
                                           "Actividad", "", "teacher", None,
                                           "porcentajes", snapshot)
        assignment = self.store.open_assignments_for_student("school-rubric", None, "pid-rubric")[0]
        self.assertEqual(assignment["competency_id"], "porcentajes")
        self.assertEqual(assignment["rubric_snapshot"], snapshot)
        self.assertTrue(self.store.submit_open_response("sub-rubric", "oa-rubric", "school-rubric",
                                                        "pid-rubric", "respuesta"))
        self.assertEqual(self.store.rubric_snapshot_for_submission("school-rubric", "sub-rubric"), snapshot)
        teacher_row = self.store.open_submissions_for_assignment("school-rubric", "oa-rubric")[0]
        self.assertEqual(teacher_row["rubric_snapshot"], snapshot)

    def test_open_assignment_submission_and_single_teacher_grade(self):
        self.store.create_open_assignment("oa-1", "school-a", None, "open-1", "Argumentá", "Mostrá el procedimiento", "teacher", None)
        self.assertEqual(len(self.store.open_assignments_for_student("school-a", None, "pid-a")), 1)
        self.assertEqual(self.store.open_assignments_for_student("school-b", None, "pid-a"), [])
        self.assertTrue(self.store.submit_open_response("sub-1", "oa-1", "school-a", "pid-a", "Mi procedimiento"))
        self.assertFalse(self.store.submit_open_response("sub-2", "oa-1", "school-a", "pid-a", "Otra respuesta"))
        pending = self.store.open_submissions_for_assignment("school-a", "oa-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["status"], "pendiente")
        self.assertTrue(self.store.grade_open_submission("school-a", "sub-1", "teacher-pid", 85, "Buen razonamiento", {"argumentacion": 4}))
        self.assertFalse(self.store.grade_open_submission("school-a", "sub-1", "teacher-pid", 90, "Cambio", {}))
        result = self.store.open_submission_for_student("school-a", "sub-1", "pid-a")
        self.assertEqual(result["score"], 85)
        self.assertEqual(result["feedback"], "Buen razonamiento")
        self.assertIsNone(self.store.open_submission_for_student("school-a", "sub-1", "pid-b"))
        self.assertTrue(self.store.submit_open_response("sub-2", "oa-1", "school-a", "pid-a", "Segunda versión"))
        self.assertFalse(self.store.submit_open_response("sub-3", "oa-1", "school-a", "pid-a", "No debe duplicar un pendiente"))
        latest = self.store.open_assignments_for_student("school-a", None, "pid-a")[0]
        self.assertEqual(latest["submission_id"], "sub-2")
        self.assertEqual(latest["attempt_number"], 2)
        self.assertEqual(latest["status"], "pendiente")
        history = self.store.open_submission_history_for_student("school-a", "oa-1", "pid-a")
        self.assertEqual([row["attempt_number"] for row in history], [2, 1])
        self.assertEqual(history[1]["score"], 85)
        self.assertEqual(history[1]["response"], "Mi procedimiento")
        teacher_history = self.store.open_submission_history_for_teacher("school-a", "sub-2")
        self.assertEqual(len(teacher_history), 2)
        self.assertNotIn("pid", teacher_history[0])
        self.assertEqual(self.store.open_submissions_for_assignment("school-a", "oa-1")[0]["id"], "sub-2")
        self.assertEqual(self.store.open_assignments_for_teacher("school-a")[0]["pending"], 1)

    def test_lti_handoff_jti_is_consumed_once(self):
        self.assertTrue(self.store.consume_token("jti-unico"))
        self.assertFalse(self.store.consume_token("jti-unico"))
        self.assertTrue(self.store.consume_token("jti-distinto"))

    def test_old_network_table_migrates_existing_memberships_to_pending(self):
        path = f"{self.tmp.name}/legacy.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE tenant_networks (network_id TEXT NOT NULL, tenant_id TEXT NOT NULL, PRIMARY KEY (network_id, tenant_id))")
        conn.execute("INSERT INTO tenant_networks (network_id, tenant_id) VALUES ('red-old', 'school-old')")
        conn.commit()
        conn.close()
        migrated = Store(f"sqlite:///{path}")
        try:
            self.assertEqual(migrated.network_tenants("red-old"), [])
            self.assertEqual(migrated.pending_network_tenants("red-old"), ["school-old"])
        finally:
            migrated._conn.close()

    def test_school_can_withdraw_accepted_network_consent(self):
        self.store.add_network_tenant("red-revoke", "school-revoke")
        self.assertTrue(self.store.answer_invite("red-revoke", "school-revoke", True))
        self.assertEqual(self.store.network_memberships("school-revoke"), ["red-revoke"])
        self.assertTrue(self.store.leave_network("red-revoke", "school-revoke"))
        self.assertEqual(self.store.network_memberships("school-revoke"), [])
        self.assertEqual(self.store.network_tenants("red-revoke"), [])
        self.assertFalse(self.store.leave_network("red-revoke", "school-revoke"))

    def test_network_membership_is_pending_until_school_accepts(self):
        self.store.add_network_tenant("red", "school-a")
        self.assertEqual(self.store.network_tenants("red"), [])
        self.assertEqual(self.store.pending_network_tenants("red"), ["school-a"])
        self.assertEqual(self.store.pending_invites("school-a"), ["red"])
        self.assertTrue(self.store.answer_invite("red", "school-a", True))
        self.assertEqual(self.store.network_tenants("red"), ["school-a"])
        self.assertFalse(self.store.answer_invite("red", "school-a", False))
        self.store.add_network_tenant("red", "school-b")
        self.assertTrue(self.store.answer_invite("red", "school-b", False))
        self.assertEqual(self.store.pending_network_tenants("red"), [])

    def test_record_answer_is_atomic_and_rejects_stale_version(self):
        self.store.create_session("answer-1", "esc", "pid-answer", "practica", {"step": 0})
        initial = self.store.load_session("answer-1", "esc")
        self.assertEqual(initial["version"], 0)

        self.assertTrue(self.store.record_answer(
            "answer-1", "esc", initial["version"], {"step": 1},
            "item-1", "A", 1.0, None, 2.5
        ))
        updated = self.store.load_session("answer-1", "esc")
        self.assertEqual(updated["version"], 1)
        self.assertEqual(updated["state"], {"step": 1})

        self.assertFalse(self.store.record_answer(
            "answer-1", "esc", initial["version"], {"step": 2},
            "item-2", "B", 0.0, "error", 3.0
        ))
        self.assertEqual(self.store.load_session("answer-1", "esc")["state"], {"step": 1})
        self.assertEqual(len(self.store.responses_for_pid("esc", "pid-answer")), 1)

    def test_concurrent_answers_from_same_version_only_commit_once(self):
        self.store.create_session("answer-race", "esc", "pid-race", "practica", {"step": 0})
        barrier = threading.Barrier(2)

        def submit(index):
            barrier.wait()
            return self.store.record_answer(
                "answer-race", "esc", 0, {"step": index},
                f"item-{index}", "A", 1.0, None, 2.0
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, (1, 2)))
        self.assertCountEqual(outcomes, [True, False])
        self.assertEqual(self.store.load_session("answer-race", "esc")["version"], 1)
        self.assertEqual(len(self.store.responses_for_pid("esc", "pid-race")), 1)

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
        self.assertTrue(self.store.add_review("template:T1", "docente-1", "aprobar", "", {k: True for k in R.CHECKLIST}))
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
        self.assertFalse(                                      # un revisor no vota dos veces
            self.store.add_review("template:T1", "docente-1", "aprobar", "", {})
        )
        self.assertEqual(len(self.store.reviews("template:T1")), 1)

    def test_concurrent_review_submission_has_one_winner_across_connections(self):
        other = Store(f"sqlite:///{self.tmp.name}/t.db")
        barrier = threading.Barrier(2)
        scope = "template:T3"
        try:
            def submit(store):
                barrier.wait(timeout=5)
                return store.add_review(scope, "curador-1", "aprobar", "", {})

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, (self.store, other)))
            self.assertCountEqual(results, [True, False])
            self.assertEqual(len(self.store.reviews(scope)), 1)
        finally:
            other._conn.close()

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
        self.st.audit("e1", "actor-p1", "exportacion_csv", "dato-privado")
        self.assertEqual(
            self.st.delete_learner("e1", "p1", actor="actor-p1"),
            {"sessions": 1, "responses": 2, "audit_events_redacted": 1},
        )
        events = self.st.audit_list("e1")
        self.assertTrue(any(e["actor"] == "redacted" and e["detail"] is None for e in events))
        self.assertFalse(any(e["actor"] == "actor-p1" for e in events))
        # El bloqueo sobrevive al reinicio del Store y no contamina otra escuela.
        self.st._conn.close()
        self.st = Store(f"sqlite:///{self.tmp.name}/v5.db")
        self.assertFalse(self.st.run_if_xapi_export_allowed("e1", "p1", lambda: self.fail("exportación tras supresión")))
        marker = self.st._conn.execute(
            "SELECT pid_hash FROM xapi_erasure_blocks WHERE tenant_id = ?", ("e1",)
        ).fetchone()["pid_hash"]
        self.assertEqual(marker, hashlib.sha256(b"p1").hexdigest())
        self.assertNotEqual(marker, "p1")
        sent_other_tenant = []
        self.assertTrue(self.st.run_if_xapi_export_allowed("e2", "p1", lambda: sent_other_tenant.append("ok")))
        self.assertEqual(sent_other_tenant, ["ok"])
        self.assertTrue(any(
            e["actor"] == "system" and e["action"] == "supresion_local_de_datos"
            for e in events
        ))
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

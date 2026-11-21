"""Integration tests against PostgreSQL, including tenant RLS and school-network consent.

Set MATHEVAL_TEST_POSTGRES_ADMIN_URL and MATHEVAL_TEST_POSTGRES_URL to enable.
The CI job provisions an ephemeral PostgreSQL service and runs this module explicitly.
"""
from __future__ import annotations

import os
from pathlib import Path
import unittest
from uuid import uuid4
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import psycopg

from api.app.store import Store


ADMIN_URL = os.getenv("MATHEVAL_TEST_POSTGRES_ADMIN_URL")
APP_URL = os.getenv("MATHEVAL_TEST_POSTGRES_URL")


@unittest.skipUnless(ADMIN_URL and APP_URL, "PostgreSQL integration URLs not configured")
class TestPostgresStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        with psycopg.connect(ADMIN_URL) as conn:
            for migration in (
                root / "db/001_init.sql",
                root / "db/003_migracion_v08.sql",
                root / "db/004_migracion_v09.sql",
                root / "db/005_migracion_v10.sql",
                root / "db/006_migracion_v11.sql",
                root / "db/007_migracion_v12.sql",
                root / "db/008_migracion_v13.sql",
                root / "db/009_migracion_v14.sql",
                root / "db/010_migracion_v15.sql",
                root / "db/011_migracion_v16.sql",
                root / "db/012_migracion_v17.sql",
            ):
                conn.execute(migration.read_text(encoding="utf-8"), prepare=False)
        cls.store = Store(APP_URL)

    def test_network_invitation_rls_and_explicit_consent(self):
        suffix = uuid4().hex
        network, school, unrelated = f"net-{suffix}", f"school-{suffix}", f"other-{suffix}"

        self.store.add_network_tenant(network, school)
        self.assertEqual(self.store.pending_network_tenants(network), [school])
        self.assertEqual(self.store.network_tenants(network), [])
        self.assertEqual(self.store.pending_invites(school), [network])
        self.assertEqual(self.store.pending_invites(unrelated), [])

        self.assertTrue(self.store.answer_invite(network, school, True))
        self.assertFalse(self.store.answer_invite(network, school, True))
        self.assertEqual(self.store.network_tenants(network), [school])
        self.assertEqual(self.store.pending_invites(school), [])

    def test_school_can_revoke_accepted_network_consent(self):
        suffix = uuid4().hex
        network, school = f"net-revoke-{suffix}", f"school-revoke-{suffix}"
        self.store.add_network_tenant(network, school)
        self.assertTrue(self.store.answer_invite(network, school, True))
        self.assertEqual(self.store.network_memberships(school), [network])
        self.assertTrue(self.store.leave_network(network, school))
        self.assertEqual(self.store.network_memberships(school), [])
        self.assertEqual(self.store.network_tenants(network), [])

    def test_school_cannot_forge_network_memberships(self):
        suffix = uuid4().hex
        school = f"school-{suffix}"
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(APP_URL) as conn:
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (school,))
                conn.execute(
                    "INSERT INTO tenant_networks (network_id, tenant_id, accepted) VALUES (%s, %s, false)",
                    (f"forged-network-{suffix}", school),
                )

    def test_open_assignment_deadline_is_enforced_by_postgres(self):
        suffix = uuid4().hex
        tenant, pid, assignment = f"school-deadline-{suffix}", f"student-{suffix}", f"assignment-{suffix}"
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.store.create_open_assignment(assignment, tenant, None, "open-item", "Vencida", "", "teacher", past)
        self.assertTrue(self.store.open_assignment_expired(tenant, assignment))
        self.assertFalse(self.store.submit_open_response(f"submission-{suffix}", assignment, tenant, pid, "late"))
        self.assertEqual(self.store.open_submissions_for_assignment(tenant, assignment), [])

    def test_open_response_review_is_tenant_scoped_and_persisted(self):
        suffix = uuid4().hex
        tenant, other, pid = f"school-open-{suffix}", f"other-open-{suffix}", f"student-open-{suffix}"
        assignment = f"assignment-{suffix}"
        submission = f"submission-{suffix}"
        self.store.create_open_assignment(assignment, tenant, None, "open-item", "Respuesta argumentada", "", "teacher", None)
        self.assertEqual(len(self.store.open_assignments_for_student(tenant, None, pid)), 1)
        self.assertEqual(self.store.open_assignments_for_student(other, None, pid), [])
        self.assertTrue(self.store.submit_open_response(submission, assignment, tenant, pid, "Desarrollo razonado"))
        self.assertFalse(self.store.submit_open_response(f"duplicate-{suffix}", assignment, tenant, pid, "Otra entrega"))
        self.assertEqual(self.store.open_assignments_for_teacher(tenant)[0]["pending"], 1)
        self.assertTrue(self.store.grade_open_submission(tenant, submission, "teacher-pseudonym", 91, "Muy bien", {"argumentacion": 4}))
        self.assertFalse(self.store.grade_open_submission(tenant, submission, "teacher-pseudonym", 95, "Revisión duplicada", {}))
        self.assertEqual(self.store.open_submission_for_student(tenant, submission, pid)["score"], 91)
        self.assertIsNone(self.store.open_submission_for_student(other, submission, pid))

    def test_session_rows_are_isolated_by_tenant(self):
        suffix = uuid4().hex
        session_id, tenant = f"session-{suffix}", f"tenant-{suffix}"
        self.store.create_session(session_id, tenant, "pseudonym-only", "practica", {"step": 1})

        row = self.store.load_session(session_id, tenant)
        self.assertIsNotNone(row)
        self.assertEqual(row["state"], {"step": 1})
        self.assertIsNone(self.store.load_session(session_id, f"other-{suffix}"))

    def test_session_state_and_result_updates_are_allowed(self):
        suffix = uuid4().hex
        session_id, tenant = f"session-update-{suffix}", f"tenant-update-{suffix}"
        self.store.create_session(session_id, tenant, "pseudonym-only", "practica", {"step": 1})
        self.store.save_session(session_id, tenant, {"step": 2})
        self.assertEqual(self.store.load_session(session_id, tenant)["state"], {"step": 2})
        result = {"level": 3, "answered": 12}
        self.store.save_session(session_id, tenant, {"step": 3}, result)
        row = self.store.load_session(session_id, tenant)
        self.assertEqual(row["state"], {"step": 3})
        self.assertEqual(row["result"], result)

    def test_atomic_answer_rejects_stale_version(self):
        suffix = uuid4().hex
        session_id, tenant, pid = f"answer-{suffix}", f"tenant-answer-{suffix}", f"pid-{suffix}"
        self.store.create_session(session_id, tenant, pid, "practica", {"step": 0})
        initial = self.store.load_session(session_id, tenant)
        self.assertEqual(initial["version"], 0)

        self.assertTrue(self.store.record_answer(
            session_id, tenant, initial["version"], {"step": 1},
            "item-1", "A", 1.0, None, 2.0
        ))
        self.assertFalse(self.store.record_answer(
            session_id, tenant, initial["version"], {"step": 2},
            "item-2", "B", 0.0, "error", 3.0
        ))
        self.assertEqual(self.store.load_session(session_id, tenant)["state"], {"step": 1})
        self.assertEqual(len(self.store.responses_for_pid(tenant, pid)), 1)

    def test_delete_learner_redacts_audit_actor_inside_tenant_scope(self):
        suffix = uuid4().hex
        tenant, pid, actor = f"tenant-erase-{suffix}", f"pid-erase-{suffix}", f"actor-erase-{suffix}"
        self.store.create_session(f"erase-{suffix}", tenant, pid, "practica", {"step": 0})
        self.store.audit(tenant, actor, "exportacion_csv", "dato-privado")
        out = self.store.delete_learner(tenant, pid, actor=actor)
        self.assertEqual(out["sessions"], 1)
        self.assertEqual(out["audit_events_redacted"], 1)
        events = self.store.audit_list(tenant)
        self.assertTrue(any(e["actor"] == "redacted" and e["detail"] is None for e in events))
        self.assertFalse(any(e["actor"] == actor for e in events))

    def test_xapi_export_and_erasure_share_a_durable_tenant_lock(self):
        suffix = uuid4().hex
        tenant, pid = f"tenant-xapi-erase-{suffix}", f"pid-xapi-erase-{suffix}"
        self.store.create_session(f"xapi-erase-{suffix}", tenant, pid, "practica", {"step": 0})
        sent = []
        self.assertTrue(self.store.run_if_xapi_export_allowed(tenant, pid, lambda: sent.append("before")))
        self.assertEqual(sent, ["before"])

        self.store.delete_learner(tenant, pid)
        self.assertFalse(self.store.run_if_xapi_export_allowed(tenant, pid, lambda: sent.append("after")))
        self.assertEqual(sent, ["before"])

    def test_xapi_erasure_block_is_isolated_between_tenants(self):
        suffix = uuid4().hex
        pid = f"shared-pid-{suffix}"
        tenant_a, tenant_b = f"tenant-a-{suffix}", f"tenant-b-{suffix}"
        self.store.delete_learner(tenant_a, pid)
        sent = []
        self.assertFalse(self.store.run_if_xapi_export_allowed(
            tenant_a, pid, lambda: sent.append("blocked")
        ))
        self.assertTrue(self.store.run_if_xapi_export_allowed(
            tenant_b, pid, lambda: sent.append("other-tenant")
        ))
        self.assertEqual(sent, ["other-tenant"])

    def test_concurrent_xapi_send_finishes_before_erasure_and_blocks_later_sends(self):
        suffix = uuid4().hex
        tenant, pid = f"tenant-xapi-race-{suffix}", f"pid-xapi-race-{suffix}"
        started = threading.Event()
        release = threading.Event()
        sent = []

        def send():
            started.set()
            if not release.wait(timeout=10):
                raise TimeoutError("test did not release the in-flight xAPI send")
            sent.append("sent")

        with ThreadPoolExecutor(max_workers=2) as pool:
            sending = pool.submit(self.store.run_if_xapi_export_allowed, tenant, pid, send)
            self.assertTrue(started.wait(timeout=5))
            deleting = pool.submit(self.store.delete_learner, tenant, pid)
            self.assertFalse(deleting.done(), "erasure must wait for the in-flight send lock")
            release.set()
            self.assertTrue(sending.result(timeout=10))
            deleting.result(timeout=10)

        self.assertEqual(sent, ["sent"])
        self.assertFalse(self.store.run_if_xapi_export_allowed(tenant, pid, lambda: sent.append("late")))
        self.assertEqual(sent, ["sent"])

    def test_app_role_cannot_modify_immutable_audit_columns(self):
        suffix = uuid4().hex
        tenant = f"tenant-audit-perms-{suffix}"
        with psycopg.connect(APP_URL) as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute(
                    "UPDATE audit_log SET action = %s WHERE tenant_id = %s",
                    ("tampered", tenant),
                )

    def test_concurrent_postgres_answers_from_same_version_commit_once(self):
        suffix = uuid4().hex
        session_id, tenant, pid = f"answer-race-{suffix}", f"tenant-race-{suffix}", f"pid-race-{suffix}"
        self.store.create_session(session_id, tenant, pid, "practica", {"step": 0})
        barrier = threading.Barrier(2)

        def submit(index):
            barrier.wait()
            return self.store.record_answer(
                session_id, tenant, 0, {"step": index},
                f"item-{index}", "A", 1.0, None, 2.0
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, (1, 2)))
        self.assertCountEqual(outcomes, [True, False])
        self.assertEqual(self.store.load_session(session_id, tenant)["version"], 1)
        self.assertEqual(len(self.store.responses_for_pid(tenant, pid)), 1)

    def test_concurrent_postgres_template_reviews_commit_once(self):
        scope = f"template:T3:{uuid4().hex}"
        barrier = threading.Barrier(2)

        def submit():
            barrier.wait(timeout=5)
            return self.store.add_review(scope, "curator-one", "aprobar", "", {"quality": True})

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: submit(), range(2)))

        self.assertCountEqual(outcomes, [True, False])
        reviews = self.store.reviews(scope)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["reviewer"], "curator-one")

    def test_consent_upsert_can_update_existing_tenant_settings(self):
        tenant = f"consent-{uuid4().hex}"
        self.store.attest_consent(tenant, "teacher-one")
        self.store.attest_consent(tenant, "teacher-two")
        settings = self.store.tenant_settings(tenant)
        self.assertEqual(settings["consent_attested_by"], "teacher-two")
        self.assertIsNotNone(settings["consent_attested_at"])


    def test_shared_rate_limit_is_atomic_across_postgres_connections(self):
        from api.app.limits import RateLimiter
        suffix = uuid4().hex
        key = f"pg-rate-{suffix}"
        limiters = [RateLimiter(self.store, lambda: 120.0) for _ in range(2)]
        barrier = threading.Barrier(12)

        def hit(index):
            barrier.wait()
            return limiters[index % 2].allow(key, 5, 60)

        with ThreadPoolExecutor(max_workers=12) as pool:
            outcomes = list(pool.map(hit, range(12)))
        self.assertEqual(sum(outcomes), 5)
        self.assertFalse(RateLimiter(self.store, lambda: 120.0).allow(key, 5, 60))
        self.assertTrue(RateLimiter(self.store, lambda: 180.0).allow(key, 5, 60))

    def test_lti_handoff_jti_is_single_use(self):
        jti = f"jti-{uuid4().hex}"
        self.assertTrue(self.store.consume_token(jti))
        self.assertFalse(self.store.consume_token(jti))


if __name__ == "__main__":
    unittest.main()

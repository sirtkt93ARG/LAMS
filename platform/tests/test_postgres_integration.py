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

    def test_consent_upsert_can_update_existing_tenant_settings(self):
        tenant = f"consent-{uuid4().hex}"
        self.store.attest_consent(tenant, "teacher-one")
        self.store.attest_consent(tenant, "teacher-two")
        settings = self.store.tenant_settings(tenant)
        self.assertEqual(settings["consent_attested_by"], "teacher-two")
        self.assertIsNotNone(settings["consent_attested_at"])

    def test_lti_handoff_jti_is_single_use(self):
        jti = f"jti-{uuid4().hex}"
        self.assertTrue(self.store.consume_token(jti))
        self.assertFalse(self.store.consume_token(jti))


if __name__ == "__main__":
    unittest.main()

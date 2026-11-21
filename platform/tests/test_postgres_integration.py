"""Integration tests against PostgreSQL, including tenant RLS and school-network consent.

Set MATHEVAL_TEST_POSTGRES_ADMIN_URL and MATHEVAL_TEST_POSTGRES_URL to enable.
The CI job provisions an ephemeral PostgreSQL service and runs this module explicitly.
"""
from __future__ import annotations

import os
from pathlib import Path
import unittest
from uuid import uuid4

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

    def test_lti_handoff_jti_is_single_use(self):
        jti = f"jti-{uuid4().hex}"
        self.assertTrue(self.store.consume_token(jti))
        self.assertFalse(self.store.consume_token(jti))


if __name__ == "__main__":
    unittest.main()

"""End-to-end backup/restore test against an ephemeral real PostgreSQL server.

Requires MATHEVAL_TEST_POSTGRES_ADMIN_URL and pg_dump/pg_restore/psql on PATH.
The source database must already have the current Matheval migrations applied.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
from psycopg import sql


ADMIN_URL = os.getenv("MATHEVAL_TEST_POSTGRES_ADMIN_URL")
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "postgres_backup.py"


@unittest.skipUnless(ADMIN_URL, "PostgreSQL backup integration URL not configured")
class TestPostgresBackupRestore(unittest.TestCase):
    def test_backup_can_be_restored_into_a_fresh_database(self):
        target_database = f"backup_restore_{uuid4().hex[:16]}"
        parsed = urlsplit(ADMIN_URL)
        target_url = urlunsplit(parsed._replace(path=f"/{target_database}"))

        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_database)))

        try:
            with psycopg.connect(ADMIN_URL) as source:
                source_counts = {
                    "sessions": source.execute("SELECT count(*) FROM public.sessions").fetchone()[0],
                    "responses": source.execute("SELECT count(*) FROM public.responses").fetchone()[0],
                }

            with self.subTest("logical backup and restore"):
                import tempfile

                with tempfile.TemporaryDirectory(prefix="matheval-backup-") as temporary:
                    output_root = Path(temporary) / "backups"
                    output_root.mkdir(mode=0o700)
                    env = os.environ.copy()
                    env["DATABASE_URL"] = ADMIN_URL
                    backup_result = subprocess.run(
                        [sys.executable, str(SCRIPT), "backup", "--output-dir", str(output_root)],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        backup_result.returncode,
                        0,
                        f"backup failed:\\n{backup_result.stdout}\\n{backup_result.stderr}",
                    )
                    backup_dirs = [path for path in output_root.iterdir() if path.is_dir()]
                    self.assertEqual(len(backup_dirs), 1, "backup should publish exactly one directory")

                    restore_env = os.environ.copy()
                    restore_env["DATABASE_URL"] = target_url
                    restore_result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            "restore",
                            "--backup",
                            str(backup_dirs[0]),
                            "--confirm-database",
                            target_database,
                        ],
                        cwd=ROOT,
                        env=restore_env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        restore_result.returncode,
                        0,
                        f"restore failed:\\n{restore_result.stdout}\\n{restore_result.stderr}",
                    )

            with psycopg.connect(target_url) as restored:
                restored_counts = {
                    "sessions": restored.execute("SELECT count(*) FROM public.sessions").fetchone()[0],
                    "responses": restored.execute("SELECT count(*) FROM public.responses").fetchone()[0],
                }
                self.assertEqual(restored_counts, source_counts)
                self.assertTrue(
                    restored.execute(
                        "SELECT relrowsecurity FROM pg_class WHERE oid = 'public.sessions'::regclass"
                    ).fetchone()[0],
                    "row-level security must survive a logical restore",
                )
                self.assertTrue(
                    restored.execute(
                        "SELECT has_table_privilege('matheval_app', 'public.sessions', 'SELECT')"
                    ).fetchone()[0],
                    "application grants must survive a logical restore",
                )
        finally:
            with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
                admin.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        sql.Identifier(target_database)
                    )
                )


if __name__ == "__main__":
    unittest.main()

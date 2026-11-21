"""End-to-end backup/restore test against an ephemeral real PostgreSQL server.

Requires MATHEVAL_TEST_POSTGRES_ADMIN_URL and pg_dump/pg_restore/psql on PATH.
The source database must already have the current Matheval migrations applied.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
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

        probe_marker = uuid4().hex
        probe_payload = f"backup-restore-roundtrip:{probe_marker}"
        try:
            with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
                admin.execute(
                    "CREATE TABLE public.backup_restore_probe "
                    "(marker text PRIMARY KEY, payload text NOT NULL)"
                )
                admin.execute(
                    "INSERT INTO public.backup_restore_probe (marker, payload) VALUES (%s, %s)",
                    (probe_marker, probe_payload),
                )

            with psycopg.connect(ADMIN_URL) as source:
                source_counts = {
                    "sessions": source.execute("SELECT count(*) FROM public.sessions").fetchone()[0],
                    "responses": source.execute("SELECT count(*) FROM public.responses").fetchone()[0],
                }
                self.assertEqual(
                    source.execute(
                        "SELECT payload FROM public.backup_restore_probe WHERE marker = %s",
                        (probe_marker,),
                    ).fetchone(),
                    (probe_payload,),
                )

            with self.subTest("logical backup and restore"):
                with tempfile.TemporaryDirectory(prefix="matheval-backup-") as temporary:
                    output_root = Path(temporary) / "backups"
                    output_root.mkdir(mode=0o700)
                    env = os.environ.copy()
                    env["DATABASE_URL"] = ADMIN_URL
                    container_id = env.get("MATHEVAL_POSTGRES_CONTAINER")
                    if container_id:
                        wrapper_dir = Path(temporary) / "postgres-client-bin"
                        wrapper_dir.mkdir(mode=0o700)
                        wrapper_source = """#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys

container = os.environ["MATHEVAL_POSTGRES_CONTAINER"]
tool = Path(sys.argv[0]).name
arguments = sys.argv[1:]
environment = []
for key in (
    "PGHOST", "PGPORT", "PGUSER", "PGDATABASE", "PGSSLMODE",
    "PGSSLROOTCERT", "PGSSLCERT", "PGSSLKEY", "PGCONNECT_TIMEOUT", "PGAPPNAME",
):
    if os.environ.get(key):
        environment.extend(["--env", f"{key}={os.environ[key]}"])

remote_dir = f"/tmp/matheval-pg-client-{os.getpid()}"
remote_passfile = None
remote_dump = None
host_output = None
if tool == "pg_dump" and "--file" in arguments:
    output_index = arguments.index("--file") + 1
    host_output = Path(arguments[output_index])
    remote_dump = f"{remote_dir}/{host_output.name}"
    arguments[output_index] = remote_dump
elif tool == "pg_restore" and arguments and not arguments[-1].startswith("-"):
    host_input = Path(arguments[-1])
    remote_dump = f"{remote_dir}/{host_input.name}"
    subprocess.run(
        ["docker", "exec", container, "mkdir", "-p", remote_dir],
        check=True,
    )
    subprocess.run(
        ["docker", "cp", str(host_input), f"{container}:{remote_dump}"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    arguments[-1] = remote_dump

if remote_dump and host_output:
    subprocess.run(
        ["docker", "exec", container, "mkdir", "-p", remote_dir],
        check=True,
    )

host_passfile = os.environ.get("PGPASSFILE")
if host_passfile:
    if remote_passfile is None:
        remote_passfile = f"{remote_dir}/pgpass"
    else:
        remote_passfile = f"{remote_dir}/pgpass"
    subprocess.run(
        ["docker", "exec", container, "mkdir", "-p", remote_dir],
        check=True,
    )
    subprocess.run(
        ["docker", "cp", host_passfile, f"{container}:{remote_passfile}"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["docker", "exec", container, "chmod", "600", remote_passfile],
        check=True,
    )
    environment.extend(["--env", f"PGPASSFILE={remote_passfile}"])

try:
    result = subprocess.run(
        ["docker", "exec", *environment, container, tool, *arguments],
        check=False,
    )
    if result.returncode == 0 and host_output and remote_dump:
        subprocess.run(
            ["docker", "cp", f"{container}:{remote_dump}", str(host_output)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    raise SystemExit(result.returncode)
finally:
    subprocess.run(
        ["docker", "exec", container, "rm", "-rf", remote_dir],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
"""
                        for tool in ("pg_dump", "pg_restore", "psql"):
                            wrapper = wrapper_dir / tool
                            wrapper.write_text(wrapper_source, encoding="utf-8")
                            wrapper.chmod(0o700)
                        env["PATH"] = str(wrapper_dir) + os.pathsep + env["PATH"]
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
                    restore_env["PATH"] = env["PATH"]
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

            if restore_result.returncode != 0:
                return

            with psycopg.connect(target_url) as restored:
                restored_counts = {
                    "sessions": restored.execute("SELECT count(*) FROM public.sessions").fetchone()[0],
                    "responses": restored.execute("SELECT count(*) FROM public.responses").fetchone()[0],
                }
                self.assertEqual(restored_counts, source_counts)
                self.assertEqual(
                    restored.execute(
                        "SELECT payload FROM public.backup_restore_probe WHERE marker = %s",
                        (probe_marker,),
                    ).fetchone(),
                    (probe_payload,),
                    "the exact sentinel row and payload must survive backup and restore",
                )
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
                admin.execute("DROP TABLE IF EXISTS public.backup_restore_probe")


if __name__ == "__main__":
    unittest.main()

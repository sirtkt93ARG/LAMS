import json
import os
import stat
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts.postgres_backup import backup, backup_directory_name, client_major_version, connection_environment, digest, load_and_verify_backup, restore, server_major_version


class TestPostgresBackupSafety(unittest.TestCase):
    def test_major_version_parsers(self):
        self.assertEqual(server_major_version("16.16 (Debian 16.16-1)"), 16)
        self.assertEqual(client_major_version("pg_dump (PostgreSQL) 16.16 (Debian 16.16-1)"), 16)
        with self.assertRaises(ValueError):
            server_major_version("unknown")
        with self.assertRaises(ValueError):
            client_major_version("unknown")
    def test_connection_url_is_mapped_to_libpq_environment_and_private_pgpass(self):
        database, env, passfile = connection_environment(
            "postgresql://matheval:p%3Aa%5Css@db.internal:5433/matheval%20prod?sslmode=verify-full"
        )
        try:
            self.assertEqual(database, "matheval prod")
            self.assertEqual(env["PGHOST"], "db.internal")
            self.assertEqual(env["PGPORT"], "5433")
            self.assertEqual(env["PGUSER"], "matheval")
            self.assertEqual(env["PGSSLMODE"], "verify-full")
            self.assertEqual(stat.S_IMODE(os.stat(passfile).st_mode), 0o600)
            self.assertIn(r"db.internal:5433:matheval prod:matheval:p\:a\\ss", Path(passfile).read_text())
        finally:
            if passfile:
                Path(passfile).unlink(missing_ok=True)

    def test_rejects_newline_in_password(self):
        with self.assertRaises(ValueError):
            connection_environment("postgresql://user:bad%0Ainjection@localhost/db")

    def test_rejects_non_postgres_url(self):
        with self.assertRaises(ValueError):
            connection_environment("sqlite:///local.db")

    def test_backup_directory_name_cannot_escape_output_root(self):
        name = backup_directory_name("../outside/../../db", "20261121T000000Z")
        self.assertNotIn("/", name)
        self.assertNotEqual(name, "..")

    def test_backup_refuses_world_readable_destination_without_chmodding_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "public-backups"
            root.mkdir(mode=0o755)
            os.chmod(root, 0o755)
            args = Namespace(database_url="postgresql://user@localhost/db", output_dir=str(root))
            with patch("scripts.postgres_backup.connection_environment", side_effect=AssertionError("must not connect")):
                with self.assertRaisesRegex(ValueError, "permisos 0700"):
                    backup(args)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o755)

    def test_backup_manifest_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "backup"
            folder.mkdir()
            dump = folder / "database.dump"
            dump.write_bytes(b"synthetic custom-format archive")
            manifest = {
                "format": "pg_dump_custom",
                "database": "matheval",
                "sha256": digest(dump),
                "size_bytes": dump.stat().st_size,
            }
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            checked, loaded = load_and_verify_backup(folder)
            self.assertEqual(checked, dump)
            self.assertEqual(loaded["sha256"], manifest["sha256"])
            dump.write_bytes(b"modified archive")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_and_verify_backup(folder)

    def test_restore_requires_exact_database_confirmation(self):
        args = Namespace(
            database_url=None,
            confirm_database="wrong-name",
            backup="/not-read",
        )
        with patch("scripts.postgres_backup.connection_environment", return_value=("production", {}, "")):
            with patch("scripts.postgres_backup.run", side_effect=AssertionError("must not connect")):
                with self.assertRaisesRegex(ValueError, "Confirmación incorrecta"):
                    restore(args)

    def test_restore_refuses_nonempty_database_before_pg_restore(self):
        args = Namespace(database_url=None, confirm_database="restore_target", backup="/synthetic")
        results = iter(["pg_restore (PostgreSQL) 16.16", "16.16", "archive contents", "t", "2"])
        with patch("scripts.postgres_backup.connection_environment", return_value=("restore_target", {}, "")):
            with patch("scripts.postgres_backup.load_and_verify_backup", return_value=(Path("/synthetic/database.dump"), {"database": "source", "server_version": "16.16", "pg_dump_version": "pg_dump (PostgreSQL) 16.16"})):
                with patch("scripts.postgres_backup.run", side_effect=lambda *a, **k: next(results)) as mocked:
                    with self.assertRaisesRegex(RuntimeError, "no está vacía"):
                        restore(args)
                    self.assertEqual(mocked.call_count, 5)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Backups verificados y restauración conservadora de PostgreSQL.

Requiere pg_dump, pg_restore y psql del cliente PostgreSQL. Lee DATABASE_URL
sin exponer la contraseña en argumentos del proceso; usa un archivo pgpass temporal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def connection_environment(database_url: str) -> tuple[str, dict[str, str], str]:
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL debe usar postgres:// o postgresql://")
    database = unquote(parsed.path.lstrip("/"))
    if not database:
        raise ValueError("DATABASE_URL debe identificar una base de datos")
    env = os.environ.copy()
    if parsed.hostname:
        env["PGHOST"] = parsed.hostname
    if parsed.port:
        env["PGPORT"] = str(parsed.port)
    if parsed.username:
        env["PGUSER"] = unquote(parsed.username)
    env["PGDATABASE"] = database
    query = parse_qs(parsed.query)
    allowed = {
        "sslmode": "PGSSLMODE",
        "sslrootcert": "PGSSLROOTCERT",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "connect_timeout": "PGCONNECT_TIMEOUT",
        "application_name": "PGAPPNAME",
    }
    for key, variable in allowed.items():
        if key in query:
            env[variable] = query[key][-1]
    password = unquote(parsed.password) if parsed.password is not None else ""
    if any(ch in password for ch in "\\r\\n"):
        raise ValueError("La contraseña de DATABASE_URL contiene caracteres no admitidos")
    if password:
        host = parsed.hostname or "*"
        port = str(parsed.port or "*")
        user = unquote(parsed.username) if parsed.username else "*"
        # Escapado del formato .pgpass (dos puntos y barras invertidas).
        escaped = password.replace("\\", "\\\\").replace(":", "\\:")
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
        try:
            os.chmod(handle.name, 0o600)
            handle.write(f"{host}:{port}:{database}:{user}:{escaped}\n")
        finally:
            handle.close()
        env["PGPASSFILE"] = handle.name
        return database, env, handle.name
    return database, env, ""


def run(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"código {result.returncode}"
        raise RuntimeError(f"Falló {Path(command[0]).name}: {detail}")
    return result.stdout.strip()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_and_verify_backup(backup_dir: Path) -> tuple[Path, dict]:
    if not backup_dir.is_dir() or backup_dir.is_symlink():
        raise ValueError("La copia debe ser un directorio local existente y no un enlace simbólico")
    dump = backup_dir / "database.dump"
    manifest_path = backup_dir / "manifest.json"
    if not dump.is_file() or not manifest_path.is_file():
        raise ValueError("La copia debe contener database.dump y manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "pg_dump_custom":
        raise ValueError("Formato de backup no reconocido")
    if manifest.get("sha256") != digest(dump):
        raise ValueError("La suma SHA-256 no coincide: la copia está dañada o fue modificada")
    if manifest.get("size_bytes") != dump.stat().st_size:
        raise ValueError("El tamaño de database.dump no coincide con el manifiesto")
    return dump, manifest


def backup(args: argparse.Namespace) -> int:
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("Definí DATABASE_URL o usá --database-url")
    database, env, passfile = connection_environment(database_url)
    root = Path(args.output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    final_dir = root / f"{database}-{stamp}"
    if final_dir.exists():
        raise FileExistsError(f"Ya existe {final_dir}; no se sobrescriben copias")
    temporary = Path(tempfile.mkdtemp(prefix=".backup-", dir=root))
    os.chmod(temporary, 0o700)
    try:
        dump = temporary / "database.dump"
        run(["pg_dump", "--format=custom", "--no-owner", "--file", str(dump), "--dbname", database], env)
        os.chmod(dump, 0o600)
        # La lista del catálogo comprueba que pg_restore puede leer el archivo antes de publicarlo.
        listing = run(["pg_restore", "--list", str(dump)], env)
        if not listing:
            raise RuntimeError("pg_restore no encontró objetos en la copia")
        version = run(["psql", "--no-psqlrc", "--tuples-only", "--no-align", "--command",
                       "SHOW server_version;", "--dbname", database], env)
        dump_version = run(["pg_dump", "--version"], env)
        manifest = {
            "format": "pg_dump_custom",
            "created_at": created.isoformat(),
            "database": database,
            "server_version": version,
            "pg_dump_version": dump_version,
            "sha256": digest(dump),
            "size_bytes": dump.stat().st_size,
            "repository_revision": os.environ.get("GITHUB_SHA"),
            "roles_and_global_privileges_included": False,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(manifest_path, 0o600)
        os.replace(temporary, final_dir)
        print(f"Copia creada y verificada: {final_dir}")
        print(f"SHA-256: {manifest['sha256']}")
        return 0
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if passfile:
            Path(passfile).unlink(missing_ok=True)


def restore(args: argparse.Namespace) -> int:
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("Definí DATABASE_URL o usá --database-url")
    database, env, passfile = connection_environment(database_url)
    try:
        if args.confirm_database != database:
            raise ValueError(
                f"Confirmación incorrecta: la base destino es {database!r}; "
                "pasá --confirm-database con ese nombre exacto"
            )
        dump, manifest = load_and_verify_backup(Path(args.backup).expanduser().resolve())
        listing = run(["pg_restore", "--list", str(dump)], env)
        if not listing:
            raise RuntimeError("El catálogo del backup está vacío")
        role_exists = run([
            "psql", "--no-psqlrc", "--tuples-only", "--no-align", "--dbname", database,
            "--command", "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'matheval_app');"
        ], env)
        if role_exists.lower() != "t":
            raise RuntimeError("No existe el rol matheval_app; provisioná roles y credenciales antes de restaurar")
        objects = run([
            "psql", "--no-psqlrc", "--tuples-only", "--no-align", "--dbname", database,
            "--command",
            "SELECT "
            "(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            " WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
            " AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S','f')) + "
            "(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            " WHERE n.nspname NOT IN ('pg_catalog','information_schema')) + "
            "(SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace "
            " WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
            " AND t.typtype IN ('c','d','e','r')) + "
            "(SELECT count(*) FROM pg_extension WHERE extname <> 'plpgsql') + "
            "(SELECT count(*) FROM pg_namespace WHERE nspname NOT IN "
            " ('pg_catalog','information_schema','public') AND nspname NOT LIKE 'pg_toast%');"
        ], env)
        if not objects.isdigit() or int(objects) != 0:
            raise RuntimeError(
                f"La base destino no está vacía (objetos encontrados: {objects!r}); "
                "no se ejecutó ninguna operación destructiva"
            )
        print(f"Restaurando {manifest['database']!r} en la base vacía {database!r}...")
        run([
            "pg_restore", "--exit-on-error", "--single-transaction", "--no-owner",
            "--dbname", database, str(dump)
        ], env)
        verified = run([
            "psql", "--no-psqlrc", "--tuples-only", "--no-align", "--dbname", database,
            "--command",
            "SELECT to_regclass('public.sessions') IS NOT NULL "
            "AND to_regclass('public.responses') IS NOT NULL;"
        ], env)
        if verified.lower() != "t":
            raise RuntimeError("La restauración terminó pero no se encontraron las tablas principales")
        print(f"Restauración completada y verificada en {database!r}.")
        print("Revisá permisos, credenciales de matheval_app, extensiones y readiness antes de habilitar tráfico.")
        return 0
    finally:
        if passfile:
            Path(passfile).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("backup", help="crear y verificar una copia consistente")
    make.add_argument("--database-url", help="URL PostgreSQL; preferí DATABASE_URL para no exponer secretos")
    make.add_argument("--output-dir", default="backups", help="directorio local cifrado/protegido para las copias")
    make.set_defaults(func=backup)
    recover = sub.add_parser("restore", help="restaurar en una base PostgreSQL vacía")
    recover.add_argument("--database-url", help="URL PostgreSQL; preferí DATABASE_URL")
    recover.add_argument("--backup", required=True, help="directorio generado por el subcomando backup")
    recover.add_argument("--confirm-database", required=True, help="nombre exacto de la base destino")
    recover.set_defaults(func=restore)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (ValueError, FileExistsError, json.JSONDecodeError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

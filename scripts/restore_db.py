# -*- coding: utf-8 -*-
"""Restore a SQLite or PostgreSQL database from a backup."""

import argparse
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

from sqlalchemy.engine import make_url


def restore_sqlite(backup_path: Path, database: str) -> None:
    target_path = Path(database).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target_path.parent, suffix=".db", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        with closing(sqlite3.connect(backup_path)) as source, closing(sqlite3.connect(temp_path)) as target:
            source.backup(target)
        os.replace(temp_path, target_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def restore_postgres(backup_path: Path, database_url: str) -> None:
    executable = shutil.which("pg_restore")
    if not executable:
        raise RuntimeError("pg_restore is required for PostgreSQL restores.")
    url = make_url(database_url)
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    command = [executable, "--clean", "--if-exists", "--no-owner"]
    if url.host:
        command.extend(["--host", url.host])
    if url.port:
        command.extend(["--port", str(url.port)])
    if url.username:
        command.extend(["--username", url.username])
    command.extend(["--dbname", url.database or "", str(backup_path)])
    subprocess.run(command, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///./exam_hub.db"))
    parser.add_argument("--confirm", action="store_true", help="Required because restore replaces current data.")
    args = parser.parse_args()
    if not args.confirm:
        raise SystemExit("Restore aborted. Re-run with --confirm after stopping the application.")

    backup_path = Path(args.backup).resolve()
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    url = make_url(args.database_url)
    if url.drivername.startswith("sqlite"):
        restore_sqlite(backup_path, url.database or "")
    elif url.drivername.startswith("postgresql"):
        restore_postgres(backup_path, args.database_url)
    else:
        raise RuntimeError(f"Unsupported database driver: {url.drivername}")
    print(f"Restored {backup_path}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Create a timestamped SQLite or PostgreSQL database backup."""

import argparse
from contextlib import closing
from datetime import datetime
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

from sqlalchemy.engine import make_url


def backup_sqlite(database: str, output_dir: Path) -> Path:
    source_path = Path(database).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"exam_hub_{datetime.now():%Y%m%d_%H%M%S}.db"
    with closing(sqlite3.connect(source_path)) as source, closing(sqlite3.connect(output_path)) as target:
        source.backup(target)
    return output_path


def backup_postgres(database_url: str, output_dir: Path) -> Path:
    executable = shutil.which("pg_dump")
    if not executable:
        raise RuntimeError("pg_dump is required for PostgreSQL backups.")
    output_dir.mkdir(parents=True, exist_ok=True)
    url = make_url(database_url)
    output_path = output_dir / f"exam_hub_{datetime.now():%Y%m%d_%H%M%S}.dump"
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    command = [executable, "--format=custom", "--file", str(output_path)]
    if url.host:
        command.extend(["--host", url.host])
    if url.port:
        command.extend(["--port", str(url.port)])
    if url.username:
        command.extend(["--username", url.username])
    command.append(url.database or "")
    subprocess.run(command, check=True, env=env)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///./exam_hub.db"))
    parser.add_argument("--output-dir", default="backups")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    url = make_url(args.database_url)
    if url.drivername.startswith("sqlite"):
        output_path = backup_sqlite(url.database or "", output_dir)
    elif url.drivername.startswith("postgresql"):
        output_path = backup_postgres(args.database_url, output_dir)
    else:
        raise RuntimeError(f"Unsupported database driver: {url.drivername}")
    print(output_path)


if __name__ == "__main__":
    main()

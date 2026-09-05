# -*- coding: utf-8 -*-
"""Backup and restore utility tests."""

import sqlite3
from contextlib import closing

from scripts.backup_db import backup_sqlite
from scripts.restore_db import restore_sqlite


def test_sqlite_backup_restore_round_trip(tmp_path) -> None:
    database = tmp_path / "source.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("create table sample (id integer primary key, value text not null)")
        connection.execute("insert into sample (value) values ('before')")
        connection.commit()

    backup = backup_sqlite(str(database), tmp_path / "backups")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("update sample set value = 'after'")
        connection.commit()

    restore_sqlite(backup, str(database))
    with closing(sqlite3.connect(database)) as connection:
        value = connection.execute("select value from sample").fetchone()[0]
    assert value == "before"

"""SQLite connection and call log."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from workshop_config import settings

_local = threading.local()


def db_path() -> Path:
    return Path(settings.business_api_db)


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    path = str(path or db_path())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = connect()
    return _local.conn


def reassign(path: str) -> None:
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
    settings.business_api_db = path
    _local.conn = connect(path)


@contextmanager
def transaction():
    conn = connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

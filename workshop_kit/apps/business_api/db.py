
"""Connexion SQLite et journal d'appels."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from socle.config import reglages

_local = threading.local()


def chemin_db() -> Path:
    return Path(reglages.application_db)


def connecter(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(db_path or chemin_db())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connexion() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = connecter()
    return _local.conn


def reassigner(db_path: str) -> None:
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
    reglages.application_db = db_path
    _local.conn = connecter(db_path)


@contextmanager
def transaction():
    conn = connexion()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

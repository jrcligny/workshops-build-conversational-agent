"""Loads the sqlite-vec extension, with a clear diagnostic when loading fails."""

from __future__ import annotations

import sqlite3
import sys
from textwrap import dedent


def _message(cause: str) -> str:
    executable = sys.executable
    sqlite_version = sqlite3.sqlite_version
    python_version = sys.version.split()[0]
    return dedent(
        f"""
        Cannot load the sqlite-vec extension (vector search).

        Cause: {cause}
        Python: {python_version} ({executable})
        SQLite: {sqlite_version}

        Requirements:
        - Use an interpreter that allows loading SQLite extensions
          (`Connection.enable_load_extension`). The simplest is to install
                    Python 3.13 from python.org, then create the environment with uv:
                    `uv python install 3.13` then `uv sync --extra dev`.
                - Windows: install Python 3.13 from python.org
          (official 64-bit installer), not the Microsoft Store package if
          extension loading fails. Tick "Add python.exe to PATH".
        - macOS: Apple's Python (/usr/bin/python3) is often built without
          this option. Install Python with Homebrew (`brew install python@3.13`)
          or from python.org, then run `uv sync --python 3.13` again.
        - Linux: interpreters installed by uv usually work. Otherwise, install
          a Python built with `--enable-loadable-sqlite-extensions`.

        Check: `uv run python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"`.
        """
    ).strip()


def load_sqlite_vec(conn: sqlite3.Connection) -> str:
    """Loads sqlite-vec on the connection and returns vec_version()."""
    if not hasattr(conn, "enable_load_extension"):
        raise RuntimeError(_message("this Python interpreter does not expose enable_load_extension."))
    try:
        conn.enable_load_extension(True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            _message(f"enable_load_extension was refused ({type(exc).__name__}: {exc}).")
        ) from exc
    try:
        import sqlite_vec

        sqlite_vec.load(conn)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            _message(f"loading sqlite-vec failed ({type(exc).__name__}: {exc}).")
        ) from exc
    finally:
        try:
            conn.enable_load_extension(False)
        except Exception:  # noqa: BLE001
            pass
    try:
        version = conn.execute("select vec_version()").fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(_message(f"vec_version() is unavailable after loading ({exc}).")) from exc
    if not version:
        raise RuntimeError(_message("vec_version() returned an empty value."))
    return str(version)

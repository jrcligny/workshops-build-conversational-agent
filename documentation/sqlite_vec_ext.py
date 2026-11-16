"""Chargement de l'extension sqlite-vec, avec un diagnostic clair si cela échoue."""

from __future__ import annotations

import sqlite3
import sys
from textwrap import dedent


def _message(cause: str) -> str:
    executable = sys.executable
    version_sqlite = sqlite3.sqlite_version
    version_python = sys.version.split()[0]
    return dedent(
        f"""
        Impossible de charger l'extension sqlite-vec (recherche vectorielle).

        Cause : {cause}
        Python : {version_python} ({executable})
        SQLite : {version_sqlite}

        Prérequis :
        - Utilisez un interpréteur qui autorise le chargement d'extensions SQLite
          (`Connection.enable_load_extension`). Le plus simple est d'installer
          Python 3.15 depuis python.org, puis de créer l'environnement avec uv :
          `uv python install 3.15` puis `uv sync --extra dev`.
        - macOS : le Python d'Apple (/usr/bin/python3) est souvent compilé sans
          cette option. Installez Python avec Homebrew (`brew install python@3.15`)
          ou depuis python.org, puis relancez `uv sync --python 3.15`.
        - Windows : installez la dernière version stable depuis python.org
          (installateur 64 bits officiel), pas le paquet Microsoft Store si le
          chargement d'extensions échoue. Cochez « Add python.exe to PATH ».
        - Linux : les interpréteurs fournis par uv fonctionnent en général.
          Sinon, installez un Python compilé avec
          `--enable-loadable-sqlite-extensions`.

        Vérification : `uv run python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"`.
        """
    ).strip()


def charger_sqlite_vec(conn: sqlite3.Connection) -> str:
    """Charge sqlite-vec sur la connexion et renvoie vec_version()."""
    if not hasattr(conn, "enable_load_extension"):
        raise RuntimeError(
            _message("cet interpréteur Python n'expose pas enable_load_extension.")
        )
    try:
        conn.enable_load_extension(True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            _message(f"enable_load_extension a été refusé ({type(exc).__name__}: {exc}).")
        ) from exc
    try:
        import sqlite_vec

        sqlite_vec.load(conn)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            _message(f"le chargement de sqlite-vec a échoué ({type(exc).__name__}: {exc}).")
        ) from exc
    finally:
        try:
            conn.enable_load_extension(False)
        except Exception:  # noqa: BLE001
            pass
    try:
        version = conn.execute("select vec_version()").fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            _message(f"vec_version() est indisponible après le chargement ({exc}).")
        ) from exc
    if not version:
        raise RuntimeError(_message("vec_version() a renvoyé une valeur vide."))
    return str(version)

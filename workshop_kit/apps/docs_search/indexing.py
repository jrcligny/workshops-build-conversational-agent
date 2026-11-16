"""Corpus indexing: FTS5 + sqlite-vec (vec0 table), rebuildable from the .txt sources."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from workshop_kit.apps.docs_search.sqlite_vec_ext import load_sqlite_vec
from workshop_kit.apps.docs_search.vectors import DIM, pack, vector
from workshop_kit.shell.config import settings

CORPUS_ROOT = Path(__file__).resolve().parents[3] / "corpus"
METADATA_FILE = "metadata.yaml"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or settings.docs_search_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    load_sqlite_vec(conn)
    return conn


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        f"""
        DROP TABLE IF EXISTS passages_vec;
        DROP TABLE IF EXISTS passages;
        DROP TABLE IF EXISTS passages_fts;
        CREATE TABLE passages (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            title TEXT NOT NULL,
            section TEXT NOT NULL,
            version TEXT NOT NULL,
            address TEXT NOT NULL,
            organization TEXT NOT NULL,
            audience TEXT NOT NULL,
            text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            id UNINDEXED,
            text,
            title,
            section,
            content=''
        );
        CREATE VIRTUAL TABLE passages_vec USING vec0(
            embedding float[{DIM}] distance_metric=cosine
        );
        """
    )


def _split(text: str) -> list[tuple[str, str]]:
    """Splits on section headings (lines starting with #)."""
    sections: list[tuple[str, list[str]]] = []
    current = "Preamble"
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if buffer and any(s.strip() for s in buffer):
                sections.append((current, buffer))
            current = line.lstrip("#").strip()
            buffer = []
        else:
            buffer.append(line)
    if buffer and any(s.strip() for s in buffer):
        sections.append((current, buffer))
    if not sections:
        return [("Document", text.strip())]
    return [(title, "\n".join(lines).strip()) for title, lines in sections if "".join(lines).strip()]


def load_metadata(corpus: Path | None = None) -> list[dict]:
    root = corpus or CORPUS_ROOT
    data = yaml.safe_load((root / METADATA_FILE).read_text(encoding="utf-8"))
    return data["documents"]


def rebuild(db_path: str | Path | None = None, include_retired: bool = False, corpus: Path | None = None) -> dict:
    root = corpus or CORPUS_ROOT
    docs = load_metadata(root)
    conn = connect(db_path)
    _schema(conn)
    n_docs = 0
    n_passages = 0
    for meta in docs:
        if meta.get("retired") and not include_retired:
            continue
        text = (root / Path(meta["file"])).read_text(encoding="utf-8")
        n_docs += 1
        for index, (section, content) in enumerate(_split(text), start=1):
            pid = f"{meta['id']}::p{index}"
            cur = conn.execute(
                """INSERT INTO passages(
                    id, document_id, title, section, version, address,
                    organization, audience, text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pid,
                    meta["id"],
                    meta["title"],
                    section,
                    meta["version"],
                    meta["address"],
                    meta["organization"],
                    meta["audience"],
                    content,
                ),
            )
            conn.execute(
                "INSERT INTO passages_fts(id, text, title, section) VALUES (?, ?, ?, ?)",
                (pid, content, meta["title"], section),
            )
            conn.execute(
                "INSERT INTO passages_vec(rowid, embedding) VALUES (?, ?)",
                (cur.lastrowid, pack(vector(f"{meta['title']} {section} {content}"))),
            )
            n_passages += 1
    conn.commit()
    conn.close()
    return {"documents": n_docs, "passages": n_passages, "include_retired": include_retired}

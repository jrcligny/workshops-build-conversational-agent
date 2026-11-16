"""Indexation du corpus : FTS5 + sqlite-vec (table vec0), reconstructible depuis les .txt."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from documentation.sqlite_vec_ext import charger_sqlite_vec
from documentation.vecteurs import DIM, packs, vecteur
from socle.config import reglages

RACINE_CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def connecter(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or reglages.documentation_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    charger_sqlite_vec(conn)
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
            titre TEXT NOT NULL,
            section TEXT NOT NULL,
            version TEXT NOT NULL,
            adresse TEXT NOT NULL,
            organisation TEXT NOT NULL,
            public_vise TEXT NOT NULL,
            texte TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            id UNINDEXED,
            texte,
            titre,
            section,
            content=''
        );
        CREATE VIRTUAL TABLE passages_vec USING vec0(
            embedding float[{DIM}] distance_metric=cosine
        );
        """
    )


def _decouper(texte: str) -> list[tuple[str, str]]:
    """Découpe selon les titres de section (lignes commençant par #)."""
    sections: list[tuple[str, list[str]]] = []
    courante = "Préambule"
    tampon: list[str] = []
    for ligne in texte.splitlines():
        if ligne.startswith("#"):
            if tampon and any(s.strip() for s in tampon):
                sections.append((courante, tampon))
            courante = ligne.lstrip("#").strip()
            tampon = []
        else:
            tampon.append(ligne)
    if tampon and any(s.strip() for s in tampon):
        sections.append((courante, tampon))
    if not sections:
        return [("Document", texte.strip())]
    return [(titre, "\n".join(lignes).strip()) for titre, lignes in sections if "".join(lignes).strip()]


def charger_metadonnees(corpus: Path | None = None) -> list[dict]:
    racine = corpus or RACINE_CORPUS
    data = yaml.safe_load((racine / "metadonnees.yaml").read_text(encoding="utf-8"))
    return data["documents"]


def reconstruire(db_path: str | Path | None = None, inclure_retires: bool = False, corpus: Path | None = None) -> dict:
    racine = corpus or RACINE_CORPUS
    docs = charger_metadonnees(racine)
    conn = connecter(db_path)
    _schema(conn)
    n_docs = 0
    n_passages = 0
    for meta in docs:
        if meta.get("retire") and not inclure_retires:
            continue
        chemin = racine / Path(meta["fichier"])
        texte = chemin.read_text(encoding="utf-8")
        n_docs += 1
        for index, (section, contenu) in enumerate(_decouper(texte), start=1):
            pid = f"{meta['id']}::p{index}"
            cur = conn.execute(
                """INSERT INTO passages(
                    id, document_id, titre, section, version, adresse,
                    organisation, public_vise, texte
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pid,
                    meta["id"],
                    meta["titre"],
                    section,
                    meta["version"],
                    meta["adresse"],
                    meta["organisation"],
                    meta["public_vise"],
                    contenu,
                ),
            )
            conn.execute(
                "INSERT INTO passages_fts(id, texte, titre, section) VALUES (?, ?, ?, ?)",
                (pid, contenu, meta["titre"], section),
            )
            conn.execute(
                "INSERT INTO passages_vec(rowid, embedding) VALUES (?, ?)",
                (cur.lastrowid, packs(vecteur(f"{meta['titre']} {section} {contenu}"))),
            )
            n_passages += 1
    conn.commit()
    conn.close()
    return {"documents": n_docs, "passages": n_passages, "inclure_retires": inclure_retires}

"""Recherche hybride : FTS5 (lexical) + KNN sqlite-vec (vectoriel), filtrage par droits."""

from __future__ import annotations

from documentation.indexation import connecter
from documentation.vecteurs import packs, vecteur


def _autorise(passage: dict, organisation: str, role: str) -> bool:
    if passage["organisation"] != organisation:
        return False
    public = passage["public_vise"]
    if public in {"tous", ""}:
        return True
    return public == role


def rechercher(
    requete: str,
    organisation: str,
    role: str,
    k: int = 5,
    seuil: float = 0.05,
    db_path: str | None = None,
) -> dict:
    conn = connecter(db_path)
    try:
        tous = [dict(r) for r in conn.execute("SELECT rowid AS _rowid, * FROM passages").fetchall()]
        visibles = [p for p in tous if _autorise(p, organisation, role)]
        if not visibles:
            return {"passages": [], "aucun_passage": True, "requete": requete}

        mots = [m.lower() for m in requete.split() if len(m) > 2]
        scores_lex: dict[str, float] = {}
        try:
            q = " OR ".join(mots) if mots else requete
            rows = conn.execute(
                "SELECT id, bm25(passages_fts) AS score FROM passages_fts WHERE passages_fts MATCH ? ORDER BY score",
                (q,),
            ).fetchall()
            for row in rows:
                scores_lex[row["id"]] = -float(row["score"])
        except Exception:  # noqa: BLE001
            scores_lex = {}
        if not scores_lex:
            for p in visibles:
                texte = (p["texte"] + " " + p["titre"] + " " + p["section"]).lower()
                scores_lex[p["id"]] = sum(texte.count(m) for m in mots)

        rowid_vers_id = {int(p["_rowid"]): p["id"] for p in tous}
        k_vec = max(k * 4, min(len(tous), 50), 8)
        rows_vec = conn.execute(
            """
            SELECT rowid, distance
            FROM passages_vec
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (packs(vecteur(requete)), k_vec),
        ).fetchall()
        scores_vec: dict[str, float] = {}
        for row in rows_vec:
            ident = rowid_vers_id.get(int(row["rowid"]))
            if ident is None:
                continue
            # distance_metric=cosine : 0 = identique, 1 = orthogonal. Similarité = 1 - distance.
            scores_vec[ident] = max(0.0, 1.0 - float(row["distance"]))
    finally:
        conn.close()

    max_lex = max((max(scores_lex.values()), 1.0)) if scores_lex else 1.0
    fusion: dict[str, float] = {}
    for p in visibles:
        lex_n = max(0.0, scores_lex.get(p["id"], 0.0)) / max_lex
        vec_n = max(0.0, scores_vec.get(p["id"], 0.0))
        fusion[p["id"]] = 0.5 * lex_n + 0.5 * vec_n

    par_id = {p["id"]: p for p in visibles}
    classés = sorted(fusion.items(), key=lambda kv: kv[1], reverse=True)
    retenus = []
    for ident, score in classés:
        if score < seuil:
            continue
        p = par_id[ident]
        retenus.append(
            {
                "id": p["id"],
                "document_id": p["document_id"],
                "titre": p["titre"],
                "section": p["section"],
                "version": p["version"],
                "adresse": p["adresse"],
                "organisation": p["organisation"],
                "public_vise": p["public_vise"],
                "texte": p["texte"],
                "score": round(score, 4),
            }
        )
        if len(retenus) >= k:
            break
    return {"passages": retenus, "aucun_passage": len(retenus) == 0, "requete": requete}


def get_passage(passage_id: str, db_path: str | None = None) -> dict | None:
    conn = connecter(db_path)
    try:
        row = conn.execute("SELECT * FROM passages WHERE id = ?", (passage_id,)).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def etat_index(db_path: str | None = None) -> dict:
    conn = connecter(db_path)
    try:
        rows = conn.execute(
            "SELECT document_id, version, organisation, COUNT(*) AS n FROM passages GROUP BY document_id, version, organisation"
        ).fetchall()
        return {"documents": [dict(r) for r in rows]}
    finally:
        conn.close()

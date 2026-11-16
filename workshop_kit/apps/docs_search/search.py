"""Hybrid search: FTS5 (lexical) + sqlite-vec KNN (vector), filtered by permissions."""

from __future__ import annotations

from workshop_kit.apps.docs_search.indexing import connect
from workshop_kit.apps.docs_search.vectors import pack, vector


def _allowed(passage: dict, organization: str, role: str) -> bool:
    if passage["organization"] != organization:
        return False
    audience = passage["audience"]
    if audience in {"all", ""}:
        return True
    return audience == role


def search(
    query: str,
    organization: str,
    role: str,
    k: int = 5,
    threshold: float = 0.05,
    db_path: str | None = None,
) -> dict:
    conn = connect(db_path)
    try:
        everything = [dict(r) for r in conn.execute("SELECT rowid AS _rowid, * FROM passages").fetchall()]
        visible = [p for p in everything if _allowed(p, organization, role)]
        if not visible:
            return {"passages": [], "no_passage": True, "query": query}

        words = [w.lower() for w in query.split() if len(w) > 2]
        lexical_scores: dict[str, float] = {}
        try:
            q = " OR ".join(words) if words else query
            rows = conn.execute(
                "SELECT id, bm25(passages_fts) AS score FROM passages_fts WHERE passages_fts MATCH ? ORDER BY score",
                (q,),
            ).fetchall()
            for row in rows:
                lexical_scores[row["id"]] = -float(row["score"])
        except Exception:  # noqa: BLE001
            lexical_scores = {}
        if not lexical_scores:
            for p in visible:
                haystack = (p["text"] + " " + p["title"] + " " + p["section"]).lower()
                lexical_scores[p["id"]] = sum(haystack.count(w) for w in words)

        rowid_to_id = {int(p["_rowid"]): p["id"] for p in everything}
        k_vec = max(k * 4, min(len(everything), 50), 8)
        vector_rows = conn.execute(
            """
            SELECT rowid, distance
            FROM passages_vec
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (pack(vector(query)), k_vec),
        ).fetchall()
        vector_scores: dict[str, float] = {}
        for row in vector_rows:
            ident = rowid_to_id.get(int(row["rowid"]))
            if ident is None:
                continue
            # distance_metric=cosine: 0 = identical, 1 = orthogonal. Similarity = 1 - distance.
            vector_scores[ident] = max(0.0, 1.0 - float(row["distance"]))
    finally:
        conn.close()

    max_lex = max((max(lexical_scores.values()), 1.0)) if lexical_scores else 1.0
    fused: dict[str, float] = {}
    for p in visible:
        lex_n = max(0.0, lexical_scores.get(p["id"], 0.0)) / max_lex
        vec_n = max(0.0, vector_scores.get(p["id"], 0.0))
        fused[p["id"]] = 0.5 * lex_n + 0.5 * vec_n

    by_id = {p["id"]: p for p in visible}
    ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
    kept = []
    for ident, score in ranked:
        if score < threshold:
            continue
        p = by_id[ident]
        kept.append(
            {
                "id": p["id"],
                "document_id": p["document_id"],
                "title": p["title"],
                "section": p["section"],
                "version": p["version"],
                "address": p["address"],
                "organization": p["organization"],
                "audience": p["audience"],
                "text": p["text"],
                "score": round(score, 4),
            }
        )
        if len(kept) >= k:
            break
    return {"passages": kept, "no_passage": len(kept) == 0, "query": query}


def get_passage(passage_id: str, db_path: str | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM passages WHERE id = ?", (passage_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def index_state(db_path: str | None = None) -> dict:
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT document_id, version, organization, COUNT(*) AS n FROM passages GROUP BY document_id, version, organization"
        ).fetchall()
        return {"documents": [dict(r) for r in rows]}
    finally:
        conn.close()

"""Hybrid search: lexical coverage + sqlite-vec KNN (vector), filtered by permissions.

The FTS5 table stays available for inspection; scores are absolute (0..1), not relative to the best hit."""

from __future__ import annotations

from workshop_kit.apps.docs_search.indexing import connect
from workshop_kit.apps.docs_search.vectors import pack, terms, vector


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
    threshold: float = 0.3,
    db_path: str | None = None,
) -> dict:
    conn = connect(db_path)
    try:
        everything = [dict(r) for r in conn.execute("SELECT rowid AS _rowid, * FROM passages").fetchall()]
        visible = [p for p in everything if _allowed(p, organization, role)]
        if not visible:
            return {"passages": [], "no_passage": True, "query": query}

        # Lexical branch: share of the query's content words found in the passage (absolute, so an
        # off-topic passage matching one generic word cannot outrank the real answer).
        wanted = set(terms(query))
        lexical_scores: dict[str, float] = {}
        for p in visible:
            present = set(terms(f"{p['title']} {p['section']} {p['text']}"))
            lexical_scores[p["id"]] = len(wanted & present) / len(wanted) if wanted else 0.0
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

    fused: dict[str, float] = {}
    for p in visible:
        lex_n = lexical_scores.get(p["id"], 0.0)
        vec_n = max(0.0, vector_scores.get(p["id"], 0.0))
        fused[p["id"]] = 0.6 * lex_n + 0.4 * vec_n

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


def index_state(db_path: str | None = None, organization: str | None = None, role: str | None = None) -> dict:
    """Documents in the index. With an identity, only the documents that identity may see."""
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT document_id, version, organization, audience, COUNT(*) AS n FROM passages"
            " GROUP BY document_id, version, organization, audience"
        ).fetchall()
        if organization is not None:
            rows = [r for r in rows if _allowed(dict(r), organization, role or "")]
        return {"documents": [dict(r) for r in rows]}
    finally:
        conn.close()

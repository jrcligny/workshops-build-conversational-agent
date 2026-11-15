
"""Recherche hybride (lexicale FTS5 + vectorielle) avec filtrage par droits."""

from __future__ import annotations

from documentation.indexation import connecter
from documentation.vecteurs import cosinus, unpacks, vecteur

PUBLICS_ELARGIS = {
    "tous": {"charge_clientele", "acheteur", "comptable", "controleur_gestion", "sans_ecriture", "tous"},
}


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
        tous = [dict(r) for r in conn.execute("SELECT * FROM passages").fetchall()]
    finally:
        conn.close()
    visibles = [p for p in tous if _autorise(p, organisation, role)]
    if not visibles:
        return {"passages": [], "aucun_passage": True, "requete": requete}

    # Branche lexicale : mots de la requête présents dans le texte (complément à FTS, robuste).
    mots = [m.lower() for m in requete.split() if len(m) > 2]
    scores_lex: dict[str, float] = {}
    conn = connecter(db_path)
    try:
        try:
            # FTS5 : on essaie une requête simple, puis un repli.
            q = " OR ".join(mots) if mots else requete
            rows = conn.execute(
                "SELECT id, bm25(passages_fts) AS score FROM passages_fts WHERE passages_fts MATCH ? ORDER BY score",
                (q,),
            ).fetchall()
            for row in rows:
                # bm25 : plus le score est petit (souvent négatif), plus c'est pertinent. On inverse.
                scores_lex[row["id"]] = -float(row["score"])
        except Exception:
            scores_lex = {}
    finally:
        conn.close()
    if not scores_lex:
        for p in visibles:
            texte = (p["texte"] + " " + p["titre"] + " " + p["section"]).lower()
            scores_lex[p["id"]] = sum(texte.count(m) for m in mots)

    qvec = vecteur(requete)
    scores_vec = {p["id"]: cosinus(qvec, unpacks(p["vecteur"])) for p in visibles}

    # Fusion simple (somme normalisée des rangs inversés).
    def rangs(scores: dict[str, float]) -> dict[str, float]:
        ordonnes = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        n = max(len(ordonnes), 1)
        return {ident: (n - i) / n for i, (ident, _) in enumerate(ordonnes)}

    # Scores bruts (pas seulement des rangs) : une requête sans correspondance
    # lexicale et avec un cosinus faible peut être déclarée vide au-delà du seuil.
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
        data = dict(row)
        data.pop("vecteur", None)
        return data
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

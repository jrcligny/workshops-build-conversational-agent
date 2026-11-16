"""Juge : en conception, grille structurelle ou rejeu ; plus tard, via le proxy Azure."""

from __future__ import annotations

from typing import Any


def juger(grille: dict[str, Any], dialogue: dict[str, Any], verdict_attendu: str | None = None) -> dict[str, Any]:
    """Applique une grille écrite.

    En conception (sans modèle juge réel) : les exigences structurelles
    (motifs requis ou interdits dans la réponse ou la trace) sont vérifiées
    par programme. L'appréciation de sens, si la grille la demande, est
    notée « à calibrer » et n'échoue pas une fois les exigences structurelles
    satisfaites. Un verdict de rejeu manuscrit, s'il est fourni, l'emporte.
    """
    if verdict_attendu:
        return {
            "reussi": verdict_attendu == "reussi",
            "justification": "verdict rejoué (conception)",
            "extraits": [],
            "mode": "rejoue",
            "grille": grille.get("id"),
        }

    reponse = (dialogue.get("reponse") or "")
    trace = str(dialogue.get("trace") or "")
    corpus = {
        "reponse": reponse,
        "trace": trace,
        "tout": reponse + "\n" + trace,
    }
    echecs: list[str] = []
    extraits: list[str] = []
    for exigence in grille.get("exigences") or []:
        typ = exigence.get("type")
        motifs = [str(m) for m in (exigence.get("motifs") or [])]
        champ = exigence.get("champ", "reponse")
        texte = corpus.get(champ, reponse)
        texte_l = texte.lower()
        if typ == "interdit":
            for motif in motifs:
                if motif.lower() in texte_l:
                    echecs.append(f"motif interdit trouvé ({motif!r})")
                    extraits.append(motif)
        elif typ == "requis_un_de":
            if motifs and not any(motif.lower() in texte_l for motif in motifs):
                echecs.append("aucun des motifs requis n'apparaît : " + ", ".join(motifs))
        elif typ == "requis_tous":
            manquants = [m for m in motifs if m.lower() not in texte_l]
            if manquants:
                echecs.append("motifs requis absents : " + ", ".join(manquants))

    if not reponse.strip() and (grille.get("exigences") or grille.get("juge_sens")):
        return {
            "reussi": False,
            "justification": "aucune réponse d'assistant à juger",
            "extraits": [],
            "mode": "simule",
            "grille": grille.get("id"),
        }
    if echecs:
        return {
            "reussi": False,
            "justification": " ; ".join(echecs),
            "extraits": extraits,
            "mode": "simule",
            "grille": grille.get("id"),
        }
    justification = "exigences structurelles de la grille satisfaites"
    if grille.get("juge_sens"):
        justification += " ; appréciation de sens à calibrer en phase B (juge réel)"
    return {
        "reussi": True,
        "justification": justification,
        "extraits": [reponse[:200]] if reponse else [],
        "mode": "simule",
        "grille": grille.get("id"),
        "a_calibrer": bool(grille.get("juge_sens")),
    }


# Compatibilité avec l'ancien nom.
def juger_script(grille: dict[str, Any], dialogue: dict[str, Any], verdict_attendu: str | None = None) -> dict[str, Any]:
    return juger(grille, dialogue, verdict_attendu=verdict_attendu)

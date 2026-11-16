"""Tests de bout en bout de l'atelier 07. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from socle.config import reglages

GRILLE_PARTIEL = {
    "id": "07-annonce-resultat-partiel",
    "juge_sens": True,
    "exigences": [
        {"type": "requis_un_de", "motifs": ["partie", "partiel", "extrait", "limité", "limite", "total"]},
    ],
}

DEMANDE_INITIALE = "Je m'occupe du dossier de Martin Durand, commande CMD-1042, uniquement les livrées."


def _compaction(trace) -> dict | None:
    if isinstance(trace.get("compaction"), dict):
        return trace["compaction"]
    if isinstance(entree(trace).get("compaction"), dict):
        return entree(trace)["compaction"]
    for ev in trace.get("evenements") or []:
        if str(ev.get("type") or ev[0] if isinstance(ev, (list, tuple)) else "") == "compaction":
            return ev if isinstance(ev, dict) else {"type": "compaction"}
    if "compaction" in plat(trace).lower():
        return {"present": True}
    return None


def test_liste_bornee_et_total_declare(client_chat, observation):
    observation.reinitialiser("volume")
    tour, trace = tour_reussi(
        client_chat,
        "Quelles sont les commandes en retard de Transports Morel, et combien y en a-t-il ?",
    )
    assert outils(trace)
    plat_outils = plat(outils(trace)).lower()
    assert "total" in plat_outils or "total" in tour.texte.lower()
    appliquer_grille(GRILLE_PARTIEL, tour, trace)
    # taille du contexte relevée à chaque cycle
    assert "taille" in plat(trace).lower() or "tokens" in plat(trace).lower() or trace.get("contexte") or entree(trace).get("taille")


def test_mode_decompte(client_chat, observation):
    observation.reinitialiser("volume")
    tour, trace = tour_reussi(
        client_chat,
        "Combien y a-t-il de commandes en retard chez Transports Morel ? Je ne veux que le nombre, pas les lignes.",
    )
    plat_outils = plat(outils(trace)).lower()
    assert "decompte" in plat_outils or "décompte" in plat_outils or "count" in plat_outils or "total" in plat_outils or "combien" in tour.texte.lower() or any(ch.isdigit() for ch in tour.texte)


def test_plafond_total_minimum(client_chat, observation):
    observation.reinitialiser("volume")
    tour, trace = tour_reussi(client_chat, "Liste toutes les commandes en retard de Transports Morel, j'en veux le total exact.")
    plat_tout = (tour.texte + plat(outils(trace))).lower()
    assert "minimum" in plat_tout or "au moins" in plat_tout or "plancher" in plat_tout or "plafond" in plat_tout or "partiel" in plat_tout


def test_pas_de_compaction_en_deca_du_seuil(client_chat):
    _, trace = tour_reussi(client_chat, DEMANDE_INITIALE)
    _, trace = tour_reussi(client_chat, "Peux-tu juste confirmer le client en cours ?")
    assert _compaction(trace) is None
    assert "compaction" not in plat(trace).lower()


def test_compaction_au_dela_du_seuil_preserve_les_messages_utilisateur(client_chat):
    messages_utilisateur = [DEMANDE_INITIALE]
    _, trace = tour_reussi(client_chat, DEMANDE_INITIALE)
    seuil = int(reglages.seuil_compaction_messages)
    for i in range(seuil + 2):
        msg = f"Précision numéro {i} : je ne veux que les commandes livrées de CMD-1042."
        messages_utilisateur.append(msg)
        tour, trace = tour_reussi(client_chat, msg)
    evenement = _compaction(trace)
    assert evenement, "la trace doit contenir l'événement de compaction"
    contenu_entree = plat(entree(trace))
    assert DEMANDE_INITIALE in contenu_entree or "CMD-1042" in contenu_entree
    # les messages de l'utilisateur restent à l'identique ; seuls réponses et résultats d'outils sont résumés
    for msg in messages_utilisateur:
        assert msg in contenu_entree, f"message utilisateur attendu à l'identique dans l'entrée : {msg!r}"
    assert "résumé" in plat(trace).lower() or "resume" in plat(trace).lower() or "summary" in plat(trace).lower() or evenement.get("resume") or evenement.get("résumé")


def test_compaction_signalee_dans_l_interface(client_chat):
    tour_reussi(client_chat, DEMANDE_INITIALE)
    tour = None
    for i in range(int(reglages.seuil_compaction_messages) + 2):
        tour, _ = tour_reussi(client_chat, f"Suite du dossier Martin Durand CMD-1042 ({i}).")
    signale = "compaction" in tour.types or any(
        ev[0] in {"compaction", "mention"}
        and ("résum" in str(ev[1]).lower() or "resum" in str(ev[1]).lower() or ev[0] == "compaction")
        for ev in tour.evenements
    )
    assert signale, "l'interface doit signaler que la partie ancienne de la conversation a été résumée"

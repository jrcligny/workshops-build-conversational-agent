"""Tests de bout en bout de l'atelier 06. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


GRILLE_PARTIEL = {
    "id": "06-limite-cycles-partiel",
    "juge_sens": True,
    "exigences": [
        {"type": "requis_un_de", "motifs": ["partiel", "pas pu", "n'ai pas", "pas vérifi", "pas verifi", "incomplet", "manque"]},
    ],
}


def test_plusieurs_cycles(client_chat):
    tour, trace = tour_reussi(client_chat, "Trouve Léa Martin de Lille et donne l'état de sa commande.")
    cycles = trace.get("cycles") or outils(trace)
    assert cycles, "la boucle agentique doit produire plusieurs cycles ou appels"
    if trace.get("cycles"):
        assert len(trace["cycles"]) >= 2 or (isinstance(trace["cycles"], int) and trace["cycles"] >= 2)


def test_appels_independants_groupes(client_chat):
    _, trace = tour_reussi(
        client_chat,
        "Donne l'état de CMD-1042 et, en parallèle, le nombre de commandes de Martin Durand.",
    )
    appels = outils(trace)
    assert len(appels) >= 2
    # au moins deux appels portent le même indice de cycle, s'il est exposé
    indices = [a.get("cycle") or a.get("cycle_id") for a in appels if a.get("cycle") or a.get("cycle_id") is not None]
    if indices:
        assert len(set(indices)) < len(indices), "les appels indépendants doivent être groupés dans un même cycle"


def test_etapes_signalees_a_l_interface(client_chat):
    tour, _ = tour_reussi(client_chat, "Trouve Léa Martin de Lille et donne l'état de sa commande.")
    assert "etape" in tour.types


def test_limite_de_cycles_reponse_partielle(client_chat):
    tour, trace = tour_reussi(
        client_chat,
        "Fais un bilan complet de toutes les commandes de Transports Morel, client par client lié, sans t'arrêter.",
    )
    if "mention" in tour.types or "partiel" in tour.texte.lower():
        appliquer_grille(GRILLE_PARTIEL, tour, trace)
        return
    # à défaut d'une mention, la trace doit indiquer qu'un plafond de cycles a été atteint
    assert "limite" in plat(trace).lower() or "plafond" in plat(trace).lower() or "max_cycles" in plat(trace).lower()
    appliquer_grille(GRILLE_PARTIEL, tour, trace)


def test_interruption_arrete_sans_nouvel_appel(client_chat):
    client_chat.ouvrir()
    client_chat.interrompre()
    tour, trace = tour_reussi(
        client_chat,
        "Trouve Léa Martin de Lille, puis toutes ses commandes, puis leur détail.",
        interrompre=True,
    )
    assert "interruption" in tour.types or "interrompu" in tour.texte.lower() or "interromp" in plat(trace).lower()
    # aucun nouvel appel après l'événement d'interruption
    apres = False
    for ev_type, _ in tour.evenements:
        if ev_type == "interruption":
            apres = True
        if apres:
            assert ev_type in {"interruption", "texte", "mention", "fin", "erreur"}

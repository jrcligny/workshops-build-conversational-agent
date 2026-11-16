"""Tests de bout en bout de l'atelier 10a. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from tests.communs.client_chat import ClientChat


def test_echange_de_jeton(client_chat, observation, services):
    jeton = observation.jeton("camille-renard")
    client_chat.ouvrir(jeton_application=jeton["jeton_application"])
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-1042 ?")
    journal = journal_metier(observation)
    assert journal, "l'application doit recevoir un appel au nom de l'utilisateur"
    plat_journal = plat(journal).lower()
    assert "camille-renard" in plat_journal or "camille" in plat_journal
    assert "service-account" not in plat_journal
    assert trace.get("identite") or any("application" in str(e).lower() for e in journal)


def test_requete_sans_identite_refusee(services, observation):
    # Un jeton d'entrée (typ=entree) n'est pas accepté par l'application : le serveur d'outils
    # doit l'échanger, pas le relayer. Un tour sans échange laisse l'API refuser.
    from application.auth import emettre_jeton
    mauvais = emettre_jeton("camille-renard", "charge_clientele", "organisation-a", typ="entree")
    client = ClientChat(services["interface"])
    client.ouvrir(jeton_application=mauvais)
    tour, trace = tour_reussi(client, "Où en est la commande CMD-1042 ?")
    journal = journal_metier(observation)
    # soit aucun appel métier n'est passé (refus en amont), soit l'API a répondu 401
    codes = [e.get("code") or e.get("status") for e in journal]
    assert (not journal) or any(c in {401, 403, "401", "403"} for c in codes) or "refus" in plat(trace).lower() or "identité" in tour.texte.lower() or "identite" in tour.texte.lower()
